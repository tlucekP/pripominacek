# Připomínáček

Jednoduchá Windows miniaplikace pro plánované připomínky. Aplikace běží na pozadí v oznamovací oblasti (tray), ukládá data do `%APPDATA%\Pripominacek\settings.json` a umí volitelný autostart přes registr.

## Požadavky

- Python 3.11+
- Windows (autostart je řešen přes Windows registry)

## Instalace (dev)

```powershell
py -3 -m pip install -r requirements.txt
```

## Spuštění (dev)

```powershell
py -3 app\main.py
```

## Build do portable `.exe`

```powershell
.\build.ps1
```

Výstup:

- `dist\Pripominacek.exe`

## Funkce

- Více připomínek najednou.
- Typy opakování:
  - `once` (jednorázově, s datem)
  - `daily` (denně)
- Pop-up připomínky (always-on-top) s akcemi:
  - `Hotovo`
  - `Odložit 10 min`
- Tray menu:
  - `Otevřít`
  - `Přidat připomínku`
  - `Pozastavit vše / Obnovit`
  - `Konec`
- Zavření hlavního okna aplikaci neukončí, pouze schová.
- Autostart přes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- Přepínač vzhledu (uložený do settings):
  - Světlá
  - Tmavá
  - Pastelová zelená
  - Pastelová červená
  - Pastelová žlutá

## Soubory dat a logů

- Nastavení: `%APPDATA%\Pripominacek\settings.json`
- Log: `%APPDATA%\Pripominacek\pripominacek.log`

## Rychlý self-check

1. Spusť aplikaci a přidej dvě připomínky (`once` + `daily`).
2. Restartuj aplikaci a ověř, že připomínky zůstaly.
3. Nech doběhnout pop-up, klikni `Odložit 10 min`, po 10 minutách ověř nové zobrazení.
4. Klikni `Hotovo` a u `once` ověř automatické vypnutí.
5. Otestuj autostart checkbox (zápis/smazání registry položky).
6. Zavři okno křížkem a ověř, že proces běží dál v tray.
