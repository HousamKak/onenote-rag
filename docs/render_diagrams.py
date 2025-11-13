"""
Script to render D2 diagrams to SVG files
Run this script to generate SVG files from D2 source files
"""
import subprocess
import os
from pathlib import Path

DIAGRAM_FILES = [
    "architecture-overview.d2",
    "architecture-overview-summary.d2",
    "rag-process-flow.d2",
    "rag-process-flow-summary.d2",
    "tech-stack.d2",
    "tech-stack-summary.d2",
    "document-indexing-flow.d2",
    "document-indexing-flow-summary.d2",
    "data-sync-flow.d2",
    "data-sync-flow-summary.d2",
    "frontend-architecture.d2",
    "frontend-architecture-summary.d2",
    "backend-architecture.d2",
    "backend-architecture-summary.d2",
    "cache_sync_architecture.d2",
    "before_after_architecture.d2",
]

def render_d2_to_svg(d2_file: str, svg_file: str) -> bool:
    """Render a D2 file to SVG using the d2 CLI"""
    try:
        # Run d2 command to generate SVG with light theme
        result = subprocess.run(
            ['d2', d2_file, svg_file, '--theme=0', '--layout=elk'],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ Rendered {d2_file} -> {svg_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error rendering {d2_file}: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ D2 CLI not found. Please install D2:")
        print("   Visit: https://d2lang.com/tour/install")
        return False

def main():
    """Render all D2 files in the docs directory"""
    docs_dir = Path(__file__).parent
    
    print("🎨 Rendering D2 diagrams to SVG...\n")
    
    success_count = 0
    for d2_file in DIAGRAM_FILES:
        d2_path = docs_dir / d2_file
        svg_path = docs_dir / d2_file.replace('.d2', '.svg')
        
        if not d2_path.exists():
            print(f"⚠️  File not found: {d2_file}")
            continue
        
        if render_d2_to_svg(str(d2_path), str(svg_path)):
            success_count += 1
    
    print(f"\n✨ Rendered {success_count}/{len(DIAGRAM_FILES)} diagrams successfully!")
    print(f"\n📂 SVG files saved in: {docs_dir}")
    print(f"\n🌐 Open diagram-viewer.html in your browser to view the diagrams")

if __name__ == '__main__':
    main()
