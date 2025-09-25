# SDRT App Installation Troubleshooting Guide

## Common Issues and Solutions

### 1. "Module sdrt not found" Error

**Cause**: App not properly registered with Frappe or Python path issues.

**Solutions**:
```bash
# Solution A: Re-register the app
cd /path/to/frappe-bench
bench get-app apps/sdrt
bench build --app sdrt
bench restart

# Solution B: Check Python path
cd /path/to/frappe-bench
bench --site your-site console
>>> import sys
>>> sys.path
>>> import sdrt  # This should work now

# Solution C: Force reinstall
bench --site your-site uninstall-app sdrt --force
bench --site your-site install-app sdrt
```

### 2. "App sdrt not installed" Error

**Cause**: App not properly added to site's apps list.

**Solution**:
```bash
# Check apps.txt
cat sites/your-site/apps.txt

# If sdrt is missing, add it manually:
echo "sdrt" >> sites/your-site/apps.txt

# Then migrate
bench --site your-site migrate
```

### 3. "ImportError: No module named 'sdrt.hooks'"

**Cause**: App directory structure issue.

**Solution**:
```bash
# Check directory structure
ls -la apps/sdrt/sdrt/
# Should contain __init__.py and hooks.py

# If structure is wrong, re-extract:
rm -rf apps/sdrt
tar -xzf sdrt-app-complete.tar.gz
mv sdrt apps/
bench get-app apps/sdrt
```

### 4. Permission Issues

**Solution**:
```bash
# Fix ownership
sudo chown -R frappe:frappe /path/to/frappe-bench/apps/sdrt

# Fix permissions
chmod -R 755 /path/to/frappe-bench/apps/sdrt
```

### 5. Database Migration Issues

**Solution**:
```bash
# Force migrate
bench --site your-site migrate --skip-failing

# Or reset and reinstall
bench --site your-site uninstall-app sdrt --force
bench --site your-site install-app sdrt
```

### 6. Build Issues

**Solution**:
```bash
# Clear cache and rebuild
bench clear-cache
bench build --hard
bench restart
```

## Manual Installation Steps (if script fails)

1. **Extract package**:
   ```bash
   tar -xzf sdrt-app-complete.tar.gz
   ```

2. **Move to apps directory**:
   ```bash
   mv sdrt /path/to/frappe-bench/apps/
   ```

3. **Register app**:
   ```bash
   cd /path/to/frappe-bench
   bench get-app apps/sdrt
   ```

4. **Install on site**:
   ```bash
   bench --site your-site install-app sdrt
   ```

5. **Build and restart**:
   ```bash
   bench build --app sdrt
   bench restart
   ```

## Verification Commands

```bash
# Check if app is installed
bench --site your-site list-apps

# Check app status
bench --site your-site doctor

# Test app import
bench --site your-site console
>>> import sdrt
>>> print(sdrt.__version__)
```

## Getting Help

If you still encounter issues:
1. Check bench logs: `tail -f logs/bench.log`
2. Check site logs: `tail -f logs/your-site.log`
3. Run: `bench --site your-site doctor`