$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
python serve_range.py 8080
