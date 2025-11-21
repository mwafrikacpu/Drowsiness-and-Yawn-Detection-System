#!/usr/bin/env python
"""
Setup testing environment for DrowsiSense
"""
import os
import subprocess
import sys

def install_test_requirements():
    """Install testing requirements"""
    print(" Installing testing requirements...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements_test.txt"
        ])
        print("   Testing requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to install requirements: {e}")
        return False

def setup_test_database():
    """Setup test database"""
    print("🗄️ Setting up test database...")
    try:
        # Use environment variable for testing
        os.environ['DJANGO_SETTINGS_MODULE'] = 'drowsiness_project.settings'
        
        # Run migrations for test database
        subprocess.check_call([
            sys.executable, "manage.py", "migrate", "--run-syncdb"
        ])
        print("   Test database setup completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Database setup failed: {e}")
        return False

def run_tests():
    """Run the test suite"""
    print(" Running test suite...")
    try:
        # Run pytest with coverage
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "drowsiness_app/tests/",
            "-v",
            "--cov=drowsiness_app",
            "--cov-report=term-missing",
            "--cov-report=html"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("   All tests passed!")
            return True
        else:
            print("  ❌ Some tests failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Test execution failed: {e}")
        return False

def setup_code_quality():
    """Setup code quality tools"""
    print("🎨 Setting up code quality tools...")
    
    # Create .pre-commit-config.yaml
    pre_commit_config = """repos:
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-merge-conflict
      - id: check-yaml
"""
    
    try:
        with open('.pre-commit-config.yaml', 'w') as f:
            f.write(pre_commit_config)
        
        # Install pre-commit hooks
        subprocess.check_call([
            sys.executable, "-m", "pre_commit", "install"
        ])
        print("  ✅ Code quality tools setup completed")
        return True
    except Exception as e:
        print(f"  ⚠️ Code quality setup failed (optional): {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up DrowsiSense Testing Environment")
    print("=" * 50)
    
    success_count = 0
    total_steps = 4
    
    # Step 1: Install requirements
    if install_test_requirements():
        success_count += 1
    
    # Step 2: Setup database
    if setup_test_database():
        success_count += 1
    
    # Step 3: Setup code quality (optional)
    if setup_code_quality():
        success_count += 1
    
    # Step 4: Run tests
    if run_tests():
        success_count += 1
    
    print("\n" + "=" * 50)
    if success_count == total_steps:
        print("🎉 Testing environment setup completed successfully!")
        print("\n📋 What's ready:")
        print("  ✅ Unit tests for models and services")
        print("  ✅ Test coverage reporting")
        print("  ✅ Code quality tools (black, flake8, isort)")
        print("  ✅ Pre-commit hooks")
        
        print("\n🔧 Commands you can use:")
        print("  pytest                    # Run all tests")
        print("  pytest --cov             # Run tests with coverage")
        print("  black .                   # Format code")
        print("  flake8 .                  # Check code quality")
        print("  pre-commit run --all-files # Run all quality checks")
        
    else:
        print(f"⚠️ Setup completed with {success_count}/{total_steps} successful steps")
        print("Some features may not be available, but you can still run basic tests.")
    
    print("\n🎯 Next steps for your portfolio:")
    print("1. Add more test cases for edge cases")
    print("2. Achieve >90% test coverage")
    print("3. Add integration tests for API endpoints")
    print("4. Set up continuous integration (CI/CD)")

if __name__ == "__main__":
    main()