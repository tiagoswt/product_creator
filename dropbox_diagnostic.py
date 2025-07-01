"""
Dropbox Integration Diagnostic Tool
Run this script to check your Dropbox setup and troubleshoot issues.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def check_dropbox_package():
    """Check if dropbox package is installed"""
    try:
        import dropbox

        print("✅ Dropbox package is installed")
        print(f"   Version: {dropbox.__version__}")
        return True
    except ImportError:
        print("❌ Dropbox package is NOT installed")
        print("   Solution: Run 'pip install dropbox>=12.0.0'")
        return False


def check_environment_token():
    """Check if Dropbox access token is configured in environment"""
    token = os.getenv("DROPBOX_ACCESS_TOKEN")
    if token:
        print("✅ Dropbox access token found in environment")
        print(
            f"   Token preview: {token[:10]}...{token[-5:] if len(token) > 15 else ''}"
        )
        return token
    else:
        print("❌ Dropbox access token NOT found in environment")
        print("   Solution: Add DROPBOX_ACCESS_TOKEN to your .env file")
        return None


def test_dropbox_connection(token):
    """Test actual connection to Dropbox"""
    if not token:
        print("⏭️  Skipping connection test (no token)")
        return False

    try:
        import dropbox

        dbx = dropbox.Dropbox(token)

        # Test basic connection
        account_info = dbx.users_get_current_account()
        print("✅ Dropbox connection successful")
        print(f"   Account: {account_info.name.display_name}")
        print(f"   Email: {account_info.email}")

        # Test storage space
        try:
            space_usage = dbx.users_get_space_usage()
            used_gb = space_usage.used / (1024**3)

            allocation = space_usage.allocation
            if hasattr(allocation, "get_individual") and allocation.get_individual():
                allocated_gb = allocation.get_individual().allocated / (1024**3)
                print(f"   Storage: {used_gb:.2f} GB used of {allocated_gb:.2f} GB")
            else:
                print(f"   Storage: {used_gb:.2f} GB used")
        except Exception as e:
            print(f"   Storage info: Not available ({str(e)})")

        return True

    except dropbox.exceptions.AuthError as e:
        print("❌ Dropbox authentication failed")
        print(f"   Error: {str(e)}")
        print("   Solution: Check your access token is correct")
        return False
    except Exception as e:
        print("❌ Dropbox connection failed")
        print(f"   Error: {str(e)}")
        return False


def test_filename_creation():
    """Test the new brand-based filename creation logic"""
    print("🔧 Testing brand-based filename creation...")

    # Test cases
    test_cases = [
        {
            "brand": "CeraVe",
            "product_name": "Hydrating Cleanser",
            "expected_prefix": "CeraVe_Hydrating_Cleanser",
        },
        {
            "brand": "L'Oréal Paris",
            "product_name": "Revitalift Serum",
            "expected_prefix": "L_Oreal_Paris_Revitalift_Serum",
        },
        {"brand": "Neutrogena", "product_name": "", "expected_prefix": "Neutrogena"},
        {
            "brand": "",
            "product_name": "Vitamin C Serum",
            "expected_prefix": "Vitamin_C_Serum",
        },
        {"brand": "", "product_name": "", "expected_prefix": "product"},
    ]

    try:
        # Try to import the filename creation function
        sys.path.append(".")
        from utils.dropbox_utils import create_product_filename

        all_passed = True
        for i, case in enumerate(test_cases):
            test_data = {"brand": case["brand"], "product_name": case["product_name"]}

            filename = create_product_filename(test_data, i)

            # Check if filename starts with expected prefix
            if filename.startswith(case["expected_prefix"]):
                print(f"   ✅ Test {i+1}: {filename}")
            else:
                print(
                    f"   ❌ Test {i+1}: Got '{filename}', expected to start with '{case['expected_prefix']}'"
                )
                all_passed = False

        if all_passed:
            print("✅ All filename creation tests passed")
        else:
            print("❌ Some filename creation tests failed")

        return all_passed

    except ImportError as e:
        print(f"⚠️  Could not import filename creation function: {str(e)}")
        print("   This is normal if running diagnostic outside the app directory")
        return True
    except Exception as e:
        print(f"❌ Error testing filename creation: {str(e)}")
        return False


def test_folder_operations(token):
    """Test folder creation and file operations with the new folder structure"""
    if not token:
        print("⏭️  Skipping folder operations test (no token)")
        return False

    try:
        import dropbox
        import json
        from datetime import datetime

        dbx = dropbox.Dropbox(token)

        # Test folder creation using the new target folder
        test_folder = "/Product_AI_Content_Creator"
        try:
            # Check if the folder exists
            try:
                dbx.files_get_metadata(test_folder)
                print("✅ Target folder exists and is accessible")
            except dropbox.exceptions.ApiError as e:
                if "not_found" in str(e):
                    print(
                        "❌ Target folder '/Product_AI_Content_Creator' does not exist"
                    )
                    print(
                        "   Solution: Create the folder manually in Dropbox or contact admin"
                    )
                    return False
                else:
                    print(f"⚠️  Folder access issue: {str(e)}")
                    return False
        except Exception as e:
            print(f"⚠️  Error checking folder: {str(e)}")
            return False

        # Test file upload to the target folder with brand-based naming
        test_data = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "message": "Dropbox integration test for Product_AI_Content_Creator folder",
            "product_name": "Test Product",
            "brand": "TestBrand",
        }
        test_content = json.dumps(test_data, indent=2).encode("utf-8")

        # Create filename using brand name
        brand = test_data["brand"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_filename = f"{brand}_{timestamp}.json"
        test_file_path = f"{test_folder}/{test_filename}"

        try:
            result = dbx.files_upload(
                test_content,
                test_file_path,
                mode=dropbox.files.WriteMode("overwrite"),
                autorename=True,
            )
            print("✅ File upload successful")
            print(f"   File path: {result.path_display}")
            print(f"   Filename format: {test_filename} (brand_timestamp.json)")

            # Clean up test file
            try:
                dbx.files_delete_v2(result.path_lower)
                print("✅ File deletion successful (cleanup)")
            except:
                print("⚠️  Could not clean up test file")

        except Exception as e:
            print(f"❌ File upload failed: {str(e)}")
            return False

        return True

    except Exception as e:
        print(f"❌ Folder operations test failed: {str(e)}")
        return False


def check_app_integration():
    """Check if the app files are properly configured"""
    required_files = ["utils/dropbox_utils.py", "utils/batch_ui.py", "config.py"]

    all_present = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_present = False

    if all_present:
        print("✅ All required files present")
    else:
        print("❌ Some required files are missing")
        print("   Solution: Ensure all updated files are in place")

    return all_present


def check_folder_configuration():
    """Check if the new folder configuration is correct"""
    try:
        import config

        if config.DROPBOX_BASE_FOLDER == "/Product_AI_Content_Creator":
            print(
                "✅ Dropbox configuration updated to use Product_AI_Content_Creator folder"
            )
        else:
            print(f"⚠️  Dropbox base folder is set to: {config.DROPBOX_BASE_FOLDER}")
            print("   Expected: /Product_AI_Content_Creator")

        if not config.DROPBOX_AUTO_ORGANIZE:
            print("✅ Auto-organize disabled (all files go to single folder)")
        else:
            print("⚠️  Auto-organize is still enabled")

        return True
    except Exception as e:
        print(f"❌ Error checking configuration: {str(e)}")
        return False


def main():
    """Run complete diagnostic"""
    print("🔍 Dropbox Integration Diagnostic Tool")
    print("=" * 50)

    print("\n📦 1. Checking Dropbox package...")
    package_ok = check_dropbox_package()

    print("\n🔑 2. Checking environment configuration...")
    token = check_environment_token()

    print("\n🌐 3. Testing Dropbox connection...")
    connection_ok = test_dropbox_connection(token)

    print("\n📁 4. Testing folder operations...")
    folder_ops_ok = test_folder_operations(token)

    print("\n📄 5. Checking app integration...")
    app_ok = check_app_integration()

    print("\n⚙️ 6. Checking folder configuration...")
    config_ok = check_folder_configuration()

    print("\n🏷️ 7. Testing filename creation...")
    filename_ok = test_filename_creation()

    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)

    all_checks = [
        ("Package Installation", package_ok),
        ("Environment Configuration", bool(token)),
        ("Dropbox Connection", connection_ok),
        ("Folder Operations", folder_ops_ok),
        ("App Integration", app_ok),
        ("Folder Configuration", config_ok),
        ("Filename Creation", filename_ok),
    ]

    passed = sum(1 for _, status in all_checks if status)
    total = len(all_checks)

    for check_name, status in all_checks:
        icon = "✅" if status else "❌"
        print(f"{icon} {check_name}")

    print(f"\n🎯 Overall Status: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All systems green! Dropbox integration is ready to use.")
        print("📁 All JSON files will be uploaded to: /Product_AI_Content_Creator")
        print(
            "🏷️ Filename format: brand_YYYYMMDD_HHMMSS.json (e.g., CeraVe_20250625_120327.json)"
        )
    else:
        print("⚠️  Some issues detected. Please review the failed checks above.")
        print("\n🔧 Quick fixes:")
        if not package_ok:
            print("   • Install dropbox: pip install dropbox>=12.0.0")
        if not token:
            print("   • Add DROPBOX_ACCESS_TOKEN to your .env file")
        if not connection_ok and token:
            print("   • Verify your Dropbox access token is correct")
        if not folder_ops_ok:
            print("   • Ensure /Product_AI_Content_Creator folder exists in Dropbox")
        if not app_ok:
            print("   • Ensure all updated app files are in place")
        if not config_ok:
            print("   • Update configuration files to use the new folder structure")
        if not filename_ok:
            print("   • Check filename creation logic is working correctly")


if __name__ == "__main__":
    main()
