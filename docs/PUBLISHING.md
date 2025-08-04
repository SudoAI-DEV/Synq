# Publishing to PyPI

This document describes how to publish the `synq-db` package to PyPI using GitHub Actions automation.

## Overview

The project uses GitHub Actions for automated publishing to PyPI with the following features:
- **Trusted Publishing**: No API tokens needed, uses OpenID Connect
- **Dual Publishing**: Publishes to both TestPyPI and PyPI  
- **Tag-based Release**: Triggered by version tags (e.g., `v0.1.0`)
- **Manual Trigger**: Can be manually triggered via GitHub UI

## Setup Process

### 1. PyPI Account Setup

1. **Create PyPI Account**: Go to https://pypi.org/account/register/
2. **Create TestPyPI Account**: Go to https://test.pypi.org/account/register/
3. **Enable 2FA**: Required for PyPI publishing

### 2. Configure API Tokens

#### Get PyPI API Tokens:
1. **PyPI Token**:
   - Go to https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Name: `synq-db-github-actions`
   - Scope: Select your project (or "Entire account" for first upload)
   - Copy the token (starts with `pypi-`)

2. **TestPyPI Token** (Optional):
   - Go to https://test.pypi.org/manage/account/token/
   - Follow same steps as above

#### Add Secrets to GitHub:
1. Go to https://github.com/SudoAI-DEV/Synq
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:
   - **Name**: `PYPI_API_TOKEN`
   - **Value**: Your PyPI token (pypi-...)
   - **Name**: `TEST_PYPI_API_TOKEN` (optional)
   - **Value**: Your TestPyPI token

### 3. GitHub Repository Settings

1. Go to your repository settings
2. Navigate to **Environments** (optional)
3. Create two environments for protection:
   - `pypi` (for production releases)
   - `testpypi` (for testing)

## Release Process

### 1. Prepare Release

1. **Update Version**: Edit `synq/__init__.py` to bump version
   ```python
   __version__ = "0.2.0"  # Update version
   ```

2. **Update Changelog**: Add release notes to `CHANGELOG.md`

3. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Prepare release v0.2.0"
   git push origin main
   ```

### 2. Create Release Tag

```bash
# Create and push tag
git tag v0.2.0
git push origin v0.2.0
```

### 3. Automated Publishing

The GitHub Action will automatically:
1. **Build** the package (wheel and source distribution)
2. **Publish to TestPyPI** (for testing)
3. **Publish to PyPI** (production release)

### 4. Verify Release

1. **Check TestPyPI**: https://test.pypi.org/project/synq-db/
2. **Check PyPI**: https://pypi.org/project/synq-db/
3. **Test Installation**:
   ```bash
   pip install synq-db==0.2.0
   synq --version
   ```

## Manual Publishing (Fallback)

If you need to publish manually:

### 1. Install Tools
```bash
pip install build twine
```

### 2. Build Package
```bash
python -m build
```

### 3. Upload to TestPyPI (Optional)
```bash
python -m twine upload --repository testpypi dist/*
```

### 4. Upload to PyPI
```bash
python -m twine upload dist/*
```

## Workflow Details

The GitHub Actions workflow (`.github/workflows/release-publish.yml`) includes:

- **Triggers**: 
  - Tag pushes (`v*`)
  - Manual workflow dispatch
- **Test Job**: Runs full test suite before publishing
- **Build Job**: Creates and validates distribution files
- **TestPyPI Job**: Always publishes to TestPyPI first
- **PyPI Job**: Only publishes to PyPI on tag pushes (after TestPyPI succeeds)
- **GitHub Release**: Creates GitHub release with changelog
- **Token Authentication**: Uses secure API tokens stored in GitHub Secrets

## Troubleshooting

### Common Issues

1. **Package Name Conflicts**: 
   - The package name `synq-db` should be unique on PyPI
   - Check availability: https://pypi.org/project/synq-db/

2. **Version Conflicts**:
   - Cannot upload the same version twice
   - Always bump version before releasing

3. **API Token Issues**:
   - Ensure tokens are correctly set in GitHub Secrets
   - Check token has correct permissions for the project
   - For first upload, token may need "Entire account" scope

4. **Build Failures**:
   - Check `pyproject.toml` configuration
   - Ensure all required files are present

### Getting Help

- **PyPI Help**: https://pypi.org/help/
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Trusted Publishing Guide**: https://docs.pypi.org/trusted-publishers/

## Security Notes

- **Secure token storage**: API tokens stored as encrypted GitHub Secrets
- **Minimal permissions**: Tokens scoped to specific projects when possible
- **Environment protection**: Production releases require tag pushes
- **Audit trail**: All releases tracked in GitHub Actions logs