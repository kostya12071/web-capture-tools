# Web Downloader Documentation

This directory contains detailed documentation for the Web Content Downloader Suite.

## Documentation Index

### Core Guides
- **[README_PEEKS.md](README_PEEKS.md)** - Complete Peeks.com downloader guide with examples
- **[README_PEEKS_ARCHITECTURE.md](README_PEEKS_ARCHITECTURE.md)** - Technical architecture and design patterns
- **[TESTING.md](TESTING.md)** - Test suite documentation and validation procedures

### Feature-Specific Guides  
- **[INSTAGRAM_DEVELOPMENT_PLAN.md](INSTAGRAM_DEVELOPMENT_PLAN.md)** - Instagram downloader implementation
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Comprehensive usage examples and patterns

### Development Documentation
- **[Copilot Instructions](../.github/copilot-instructions.md)** - Development standards and coding guidelines

## Quick Navigation

**Getting Started:**
1. See main [README.md](../README.md) for installation
2. Read [README_PEEKS.md](README_PEEKS.md) for detailed usage
3. Check [TESTING.md](TESTING.md) for validation

**Architecture Understanding:**
1. Review [README_PEEKS_ARCHITECTURE.md](README_PEEKS_ARCHITECTURE.md)
2. Study modular components in `../lib/` folder
3. Examine test patterns in [TESTING.md](TESTING.md)

**Advanced Features:**
1. Check [INSTAGRAM_DEVELOPMENT_PLAN.md](INSTAGRAM_DEVELOPMENT_PLAN.md) for Instagram support
2. Review [USAGE_GUIDE.md](USAGE_GUIDE.md) for complex scenarios

## Project Structure

The documentation reflects the modular project structure:

```
scripts/          # User-facing CLI tools
lib/             # Reusable modules and components
├── scrapers/    # Site-specific extraction logic
├── capture/     # Web capture framework  
└── core/        # Shared utilities
tests/           # Comprehensive test suite
docs/            # This documentation directory
```

Each component has dedicated documentation explaining its purpose, usage, and integration patterns.