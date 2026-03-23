# Pyxel MCP Setup

This project is configured to use Pyxel MCP with the virtual environment in `test3`.

## Installed packages

- `pyxel==2.8.7`
- `pyxel-mcp==0.8.0`

## Project MCP config

The project-level MCP server definition is stored in `.mcp.json`.

```json
{
  "mcpServers": {
    "pyxel": {
      "type": "stdio",
      "command": "C:\\Users\\user\\pyxel\\test3\\test3\\Scripts\\pyxel-mcp.exe"
    }
  }
}
```

## Reinstall in a fresh environment

```powershell
.\test3\Scripts\python.exe -m pip install -r requirements.txt
```

## Notes for Codex

Your global Codex MCP configuration currently points to another environment:

`C:\Users\user\.codex\config.toml`

If you want Codex itself to use this project's `pyxel-mcp.exe`, update that file so the `mcp_servers.pyxel.command` value points to:

`C:\Users\user\pyxel\test3\test3\Scripts\pyxel-mcp.exe`
