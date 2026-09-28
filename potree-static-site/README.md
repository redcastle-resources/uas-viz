# Lightweight Potree Static Site

This folder is the smallest practical deployment pattern for serving a Potree point cloud from a static web server.

The Potree point cloud is expected to be produced using the PotreeConverter 2

## Folder layout

```text
potree-static-site/
├── index.html
├── serve.ps1
├── pointclouds/
│   └── mycloud/
│       ├── hierarchy.bin
│       ├── log.txt
│       ├── metadata.json
│       └── octree.bin
├── vendor/
│   └── potree/
│       └── ... Potree distribution files ...
└── README.md
```

## What to do

1. Download the Potree viewer distribution and copy it under `vendor/potree/`.
2. Copy your generated Potree point cloud output into `pointclouds/mycloud/`.
3. Start the local static server from this folder.
4. Open the site in a browser.

## Start locally on Windows

```powershell
cd potree-static-site
./serve.ps1
```

Then open:

```text
http://localhost:8080/
```

## If you want a cloud/static host

Upload the entire `potree-static-site/` directory to any static web host or object storage bucket that supports website hosting.

## Notes

- This is intentionally lightweight: no backend, no database, no GIS server.
- Use Potree for the point cloud itself.
- Derived TIFFs are best handled as separate raster layers or downloaded assets unless you specifically need a full GIS overlay stack.
