# SDRT App Installation Guide

## Quick Installation (Recommended)

1. **Transfer the package** to your target computer:
   ```bash
   scp sdrt-app-complete.tar.gz user@target-computer:/tmp/
   ```

2. **On the target computer**, navigate to your Frappe bench and run:
   ```bash
   cd /path/to/your/frappe-bench
   tar -xzf /tmp/sdrt-app-complete.tar.gz
   bash sdrt/install_on_target.sh YOUR_SITE_NAME
   ```

   Example:
   ```bash
   bash sdrt/install_on_target.sh mysite.localhost
   ```

## Manual Installation (if script fails)

1. **Extract the package**:
   ```bash
   tar -xzf sdrt-app-complete.tar.gz
   ```

2. **Move to apps directory**:
   ```bash
   cd /path/to/frappe-bench
   mv sdrt apps/
   ```

3. **Add to apps.txt**:
   ```bash
   echo "sdrt" >> sites/apps.txt
   ```

4. **Register with bench**:
   ```bash
   bench get-app apps/sdrt
   ```

5. **Install on site**:
   ```bash
   bench --site YOUR_SITE install-app sdrt
   ```

6. **Build and restart**:
   ```bash
   bench build --app sdrt
   bench --site YOUR_SITE migrate
   bench restart
   ```

## Troubleshooting "Module not found" Errors

If you get "module sdrt not found" errors, try these solutions:

### Solution 1: Python Path Issues
```bash
cd /path/to/frappe-bench
bench --site YOUR_SITE console
>>> import sys
>>> sys.path.append('/path/to/frappe-bench/apps')
>>> import sdrt
>>> print(sdrt.__version__)
```

### Solution 2: Reinstall the App
```bash
bench --site YOUR_SITE uninstall-app sdrt --force
bench get-app apps/sdrt
bench --site YOUR_SITE install-app sdrt
```

### Solution 3: Clear Cache and Rebuild
```bash
bench clear-cache
bench build --hard
bench restart
```

### Solution 4: Check App Structure
```bash
# Verify app structure
ls -la apps/sdrt/sdrt/
# Should show: __init__.py, hooks.py, modules.txt, etc.

# Check if app is properly registered
bench list-apps
```

## Verification Commands

After installation, verify everything works:

```bash
# Check installed apps
bench --site YOUR_SITE list-apps

# Should show sdrt in the list

# Test import in console
bench --site YOUR_SITE console
>>> import sdrt
>>> print("SDRT version:", sdrt.__version__)
>>> exit()

# Check site health
bench --site YOUR_SITE doctor
```

## File Structure Requirements

Your extracted app should have this structure:
```
sdrt/
├── pyproject.toml
├── README.md
├── license.txt
├── install_on_target.sh
├── validate_app.sh
├── INSTALLATION_TROUBLESHOOTING.md
└── sdrt/
    ├── __init__.py
    ├── hooks.py
    ├── modules.txt
    ├── patches.txt
    └── sdrt/
        └── doctype/
            └── [your doctypes]
```

## Support

If you continue to have issues:

1. Check the logs:
   ```bash
   tail -f logs/bench.log
   tail -f logs/YOUR_SITE.log
   ```

2. Run the validation script:
   ```bash
   bash sdrt/validate_app.sh
   ```

3. Check the troubleshooting guide:
   ```bash
   cat sdrt/INSTALLATION_TROUBLESHOOTING.md
   ```