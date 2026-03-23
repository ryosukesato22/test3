# Twin Drop Duel

Pyxel で動く対戦型落ちモノパズルです。左がプレイヤー、右が CPU です。

## Run

```powershell
.\test3\Scripts\python.exe .\main.py
```

## Play On The Web

Build a browser version locally:

```powershell
.\test3\Scripts\python.exe .\scripts\build_web.py
```

This creates `web/index.html`.

GitHub Pages deployment is also configured. After pushing to `main`, GitHub Actions will publish the web build.

## Controls

- `A` / `D`: move
- `S`: soft drop
- `F` / `G`: rotate
- `R`: restart
