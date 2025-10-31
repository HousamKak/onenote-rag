"""
Test script to verify OneNote integration and Microsoft Graph API connection.
"""
import os
from dotenv import load_dotenv
from backend.services.onenote_service import OneNoteService

# Load environment variables
load_dotenv('backend/.env')

def test_onenote_connection():
    """Test OneNote service connection and data retrieval."""
    
    # Get credentials from environment
    client_id = os.getenv('MICROSOFT_CLIENT_ID')
    client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
    tenant_id = os.getenv('MICROSOFT_TENANT_ID')
    
    print("=" * 60)
    print("OneNote Integration Test")
    print("=" * 60)
    print(f"\nClient ID: {client_id[:20]}..." if client_id else "Client ID: Not set")
    print(f"Tenant ID: {tenant_id[:20]}..." if tenant_id else "Tenant ID: Not set")
    print(f"Client Secret: {'*' * 20}" if client_secret else "Client Secret: Not set")
    
    if not all([client_id, client_secret, tenant_id]):
        print("\n❌ Error: Missing Microsoft Graph API credentials")
        print("Please set MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, and MICROSOFT_TENANT_ID in .env")
        return
    
    # Initialize OneNote service
    print("\n" + "-" * 60)
    print("Initializing OneNote service...")
    print("-" * 60)
    
    service = OneNoteService(client_id, client_secret, tenant_id)
    
    if not service.access_token:
        print("\n❌ Authentication failed - no access token obtained")
        print("This could mean:")
        print("  1. Credentials are invalid")
        print("  2. App doesn't have proper permissions configured")
        print("  3. Network/firewall issues")
        return
    
    print("✅ Authentication successful!")
    print(f"Access token obtained: {service.access_token[:50]}...")
    
    # Test listing notebooks
    print("\n" + "-" * 60)
    print("Fetching notebooks...")
    print("-" * 60)
    
    notebooks = service.list_notebooks()
    
    if not notebooks:
        print("\n⚠️  No notebooks found")
        print("\nPossible reasons:")
        print("  1. Using app-only authentication (service principal)")
        print("     - Service principals access organization data, not user data")
        print("     - You may need delegated permissions and user authentication")
        print("  2. The account has no OneNote notebooks")
        print("  3. App doesn't have Notes.Read permission")
        return
    
    print(f"\n✅ Found {len(notebooks)} notebook(s):")
    
    for i, notebook in enumerate(notebooks, 1):
        print(f"\n  {i}. {notebook.get('displayName', 'Unnamed')}")
        print(f"     ID: {notebook.get('id')}")
        print(f"     Created: {notebook.get('createdDateTime', 'N/A')}")
        
        # Try to get sections from first notebook
        if i == 1:
            notebook_id = notebook.get('id')
            print(f"\n     Fetching sections for this notebook...")
            sections = service.list_sections(notebook_id)
            
            if sections:
                print(f"     ✅ Found {len(sections)} section(s):")
                for j, section in enumerate(sections[:3], 1):  # Show first 3
                    print(f"        - {section.get('displayName', 'Unnamed')}")
                    
                # Try to get pages from first section
                if sections:
                    section_id = sections[0].get('id')
                    section_name = sections[0].get('displayName')
                    print(f"\n     Fetching pages from '{section_name}'...")
                    pages = service.list_pages(section_id)
                    
                    if pages:
                        print(f"     ✅ Found {len(pages)} page(s):")
                        for k, page in enumerate(pages[:3], 1):  # Show first 3
                            print(f"        - {page.get('title', 'Untitled')}")
                            
                        # Try to get content from first page
                        if pages:
                            page_id = pages[0].get('id')
                            page_title = pages[0].get('title')
                            print(f"\n     Fetching content from '{page_title}'...")
                            content = service.get_page_content(page_id)
                            
                            if content:
                                content_preview = content[:200].replace('\n', ' ')
                                print(f"     ✅ Content retrieved ({len(content)} chars)")
                                print(f"     Preview: {content_preview}...")
                            else:
                                print("     ❌ Failed to retrieve page content")
                    else:
                        print("     ⚠️  No pages found in this section")
            else:
                print("     ⚠️  No sections found in this notebook")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_onenote_connection()
