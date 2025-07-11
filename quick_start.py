#!/usr/bin/env python3
"""
Quick Start Script for Network Automation Request Sender
Easy setup and launch script
"""

import asyncio
import sys
import subprocess
from pathlib import Path


def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False


def show_menu():
    """Show the main menu"""
    print("\n🚀 Network Automation Request Sender")
    print("=" * 50)
    print("1. 🌐 Launch Web Interface")
    print("2. 🎯 Run Demo")
    print("3. 📝 Basic Usage Examples")
    print("4. 🔧 Advanced Usage Examples")
    print("5. ⚡ Interactive CLI Mode")
    print("6. 📊 Batch Processing")
    print("7. 📦 Install Dependencies")
    print("8. ❓ Help")
    print("9. 🚪 Exit")
    print("=" * 50)


def show_help():
    """Show help information"""
    print("\n📖 Help - Network Automation Request Sender")
    print("=" * 50)
    print("🌐 Web Interface:")
    print("   • User-friendly browser interface")
    print("   • Send single or batch requests")
    print("   • Real-time monitoring")
    print("   • Request history")
    print("   • Live system metrics")
    print()
    print("🎯 Demo:")
    print("   • Complete feature demonstration")
    print("   • Shows all capabilities")
    print("   • Performance testing")
    print()
    print("📝 Examples:")
    print("   • Basic: Simple request sending")
    print("   • Advanced: Complex features")
    print("   • Authentication methods")
    print("   • Error handling")
    print()
    print("⚡ Interactive CLI:")
    print("   • Command-line interface")
    print("   • Manual request submission")
    print("   • Real-time status monitoring")
    print()
    print("📊 Batch Processing:")
    print("   • Process multiple requests from file")
    print("   • YAML or JSON configuration")
    print("   • Automated execution")
    print()
    print("🔧 Configuration:")
    print("   • config/default.yaml - Main configuration")
    print("   • Customize timeouts, limits, etc.")
    print("   • Authentication templates")
    print()
    print("📁 File Structure:")
    print("   • src/ - Core source code")
    print("   • examples/ - Usage examples")
    print("   • config/ - Configuration files")
    print("   • logs/ - Log files (auto-created)")
    print("=" * 50)


async def main():
    """Main menu loop"""
    while True:
        show_menu()
        
        try:
            choice = input("\nEnter your choice (1-9): ").strip()
            
            if choice == "1":
                print("\n🌐 Starting Web Interface...")
                print("This will open a browser-based interface at http://localhost:8080")
                confirm = input("Continue? (y/n): ").strip().lower()
                if confirm == 'y':
                    subprocess.run([sys.executable, "web_interface.py"])
            
            elif choice == "2":
                print("\n🎯 Running Demo...")
                print("This will demonstrate all features of the system")
                confirm = input("Continue? (y/n): ").strip().lower()
                if confirm == 'y':
                    subprocess.run([sys.executable, "run_demo.py"])
            
            elif choice == "3":
                print("\n📝 Running Basic Examples...")
                subprocess.run([sys.executable, "examples/basic_usage.py"])
            
            elif choice == "4":
                print("\n🔧 Running Advanced Examples...")
                subprocess.run([sys.executable, "examples/advanced_usage.py"])
            
            elif choice == "5":
                print("\n⚡ Starting Interactive CLI...")
                subprocess.run([sys.executable, "main.py", "--interactive"])
            
            elif choice == "6":
                print("\n📊 Available batch files:")
                batch_files = list(Path("config").glob("*.yaml"))
                for i, file in enumerate(batch_files, 1):
                    print(f"   {i}. {file.name}")
                
                if batch_files:
                    try:
                        file_choice = int(input(f"Select file (1-{len(batch_files)}): ")) - 1
                        if 0 <= file_choice < len(batch_files):
                            batch_file = batch_files[file_choice]
                            print(f"\n📊 Processing batch file: {batch_file.name}")
                            subprocess.run([sys.executable, "main.py", "--batch", str(batch_file)])
                        else:
                            print("❌ Invalid choice")
                    except ValueError:
                        print("❌ Invalid input")
                else:
                    print("❌ No batch files found in config/ directory")
            
            elif choice == "7":
                install_dependencies()
            
            elif choice == "8":
                show_help()
            
            elif choice == "9":
                print("\n👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please select 1-9.")
            
            if choice != "9":
                input("\nPress Enter to continue...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            input("Press Enter to continue...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")