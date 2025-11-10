"""
Enhanced rate limiting and batching strategy for Microsoft Graph API.
 
This module provides configurable rate limiting to handle large OneNote syncs
without hitting API limits.
"""
import time
import logging
from typing import Optional
from datetime import datetime, timedelta
 
logger = logging.getLogger(__name__)
 
 
class RateLimiter:
    """
    Token bucket rate limiter for Microsoft Graph API.
   
    Microsoft Graph API limits:
    - 600 requests per minute per user
    - 10,000 requests per 10 minutes per app
   
    Our conservative approach:
    - Max 100 requests per minute (well below limit)
    - Automatic backoff on 429 errors
    - Configurable delays for different operations
    """
   
    def __init__(
        self,
        requests_per_minute: int = 100,
        burst_size: int = 10,
        min_interval_ms: int = 500
    ):
        """
        Initialize rate limiter.
       
        Args:
            requests_per_minute: Maximum requests per minute (default: 100, safe limit)
            burst_size: Allow burst of N requests, then throttle
            min_interval_ms: Minimum milliseconds between requests
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.min_interval = min_interval_ms / 1000.0  # Convert to seconds
       
        self.tokens = burst_size
        self.max_tokens = burst_size
        self.last_refill = time.time()
        self.last_request = 0
       
        # Statistics
        self.total_requests = 0
        self.total_waits = 0
        self.total_wait_time = 0.0
       
        logger.info(
            f"RateLimiter initialized: {requests_per_minute} req/min, "
            f"burst={burst_size}, min_interval={min_interval_ms}ms"
        )
   
    def _refill_tokens(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
       
        # Add tokens based on time elapsed
        # tokens_per_second = requests_per_minute / 60
        tokens_to_add = elapsed * (self.requests_per_minute / 60.0)
       
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
   
    def acquire(self, wait: bool = True) -> bool:
        """
        Acquire permission to make a request.
       
        Args:
            wait: If True, block until token available. If False, return immediately.
           
        Returns:
            True if request can proceed, False if would need to wait (only when wait=False)
        """
        self._refill_tokens()
       
        # Check minimum interval
        now = time.time()
        time_since_last = now - self.last_request
       
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            if not wait:
                return False
           
            logger.debug(f"Enforcing minimum interval: waiting {wait_time:.3f}s")
            time.sleep(wait_time)
            self.total_waits += 1
            self.total_wait_time += wait_time
       
        # Check tokens
        if self.tokens < 1:
            if not wait:
                return False
           
            # Calculate wait time until next token
            wait_time = (1.0 - self.tokens) / (self.requests_per_minute / 60.0)
            logger.debug(f"Token bucket empty: waiting {wait_time:.3f}s")
            time.sleep(wait_time)
            self.total_waits += 1
            self.total_wait_time += wait_time
            self._refill_tokens()
       
        # Consume token
        self.tokens -= 1
        self.last_request = time.time()
        self.total_requests += 1
       
        return True
   
    def handle_rate_limit_error(self, retry_after: Optional[int] = None):
        """
        Handle 429 Too Many Requests error.
       
        Args:
            retry_after: Seconds to wait from Retry-After header (if available)
        """
        wait_time = retry_after if retry_after else 60
       
        logger.warning(
            f"Rate limit hit (429). Waiting {wait_time}s as requested by server."
        )
       
        # Reset tokens to 0 to prevent immediate retry
        self.tokens = 0
        self.last_refill = time.time()
       
        time.sleep(wait_time)
       
        # After waiting, refill to half capacity for gradual restart
        self.tokens = self.max_tokens / 2
        self.total_waits += 1
        self.total_wait_time += wait_time
   
    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "total_requests": self.total_requests,
            "total_waits": self.total_waits,
            "total_wait_time_seconds": round(self.total_wait_time, 2),
            "current_tokens": round(self.tokens, 2),
            "requests_per_minute": self.requests_per_minute
        }
 
 
class BatchProcessor:
    """
    Batch processor for efficient API operations.
   
    Processes large lists in batches with progress reporting.
    """
   
    def __init__(self, batch_size: int = 20, show_progress: bool = True):
        """
        Initialize batch processor.
       
        Args:
            batch_size: Number of items to process per batch
            show_progress: Whether to log progress
        """
        self.batch_size = batch_size
        self.show_progress = show_progress
   
    def process_in_batches(self, items: list, process_func, description: str = "items"):
        """
        Process items in batches.
       
        Args:
            items: List of items to process
            process_func: Function to call for each item (receives item, returns result)
            description: Description for logging
           
        Returns:
            List of results from process_func
        """
        total = len(items)
        results = []
       
        if total == 0:
            return results
       
        num_batches = (total + self.batch_size - 1) // self.batch_size
       
        if self.show_progress:
            logger.info(f"Processing {total} {description} in {num_batches} batches")
       
        for batch_num in range(num_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, total)
            batch = items[start_idx:end_idx]
           
            if self.show_progress:
                logger.info(
                    f"Batch {batch_num + 1}/{num_batches}: "
                    f"Processing {description} {start_idx + 1}-{end_idx} of {total}"
                )
           
            for item in batch:
                result = process_func(item)
                if result is not None:
                    results.append(result)
       
        if self.show_progress:
            logger.info(f"Completed processing {len(results)}/{total} {description}")
       
        return results
 
 
class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts based on observed API behavior.
   
    Automatically slows down if seeing errors, speeds up if successful.
    """
   
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
       
        self.consecutive_successes = 0
        self.consecutive_errors = 0
        self.original_rpm = self.requests_per_minute
   
    def record_success(self):
        """Record a successful API call."""
        self.consecutive_successes += 1
        self.consecutive_errors = 0
       
        # After 50 consecutive successes, try to speed up slightly
        if self.consecutive_successes >= 50:
            old_rpm = self.requests_per_minute
            self.requests_per_minute = min(
                self.original_rpm,
                self.requests_per_minute * 1.1
            )
            if self.requests_per_minute != old_rpm:
                logger.info(
                    f"Speeding up: {old_rpm:.0f} → {self.requests_per_minute:.0f} req/min"
                )
            self.consecutive_successes = 0
   
    def record_error(self, is_rate_limit: bool = False):
        """
        Record an API error.
       
        Args:
            is_rate_limit: Whether this was a 429 rate limit error
        """
        self.consecutive_errors += 1
        self.consecutive_successes = 0
       
        if is_rate_limit:
            # Immediate slowdown on rate limit
            old_rpm = self.requests_per_minute
            self.requests_per_minute = max(30, self.requests_per_minute * 0.5)
            logger.warning(
                f"Rate limit hit! Slowing down: {old_rpm:.0f} → {self.requests_per_minute:.0f} req/min"
            )
        elif self.consecutive_errors >= 5:
            # Gradual slowdown on repeated errors
            old_rpm = self.requests_per_minute
            self.requests_per_minute = max(50, self.requests_per_minute * 0.8)
            logger.warning(
                f"Multiple errors detected. Slowing down: {old_rpm:.0f} → {self.requests_per_minute:.0f} req/min"
            )
            self.consecutive_errors = 0
 