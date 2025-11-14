# Audio-Sammelskript für Windows und macOS

Dieses Repository enthält das PowerShell-Skript [`scripts/audio_collect.ps1`](../scripts/audio_collect.ps1),
mit dem Sie alle verfügbaren Laufwerke nach Audiodateien durchsuchen und diese in einen
zentralen Ordner `Audio_Quelle` kopieren können.

## Voraussetzungen

* Windows 10 oder neuer (PowerShell 5.1 oder PowerShell 7) **oder** macOS mit PowerShell 7.
* Lesezugriff auf die gewünschten Laufwerke (lokal oder Netzwerk).
* Schreibrechte für den Zielordner `Audio_Quelle` (standardmäßig im Benutzerprofil).

### PowerShell auf macOS installieren

macOS bringt PowerShell nicht standardmäßig mit. Installieren Sie zunächst Homebrew
und anschließend PowerShell:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install --cask powershell
```

Starten Sie PowerShell anschließend über `pwsh` im Terminal.

## Verwendung

1. Öffnen Sie eine PowerShell-Sitzung mit ausreichenden Berechtigungen.
2. Navigieren Sie in das Verzeichnis dieses Repositories.
3. Führen Sie das Skript mit folgendem Befehl aus:

   ```powershell
   pwsh ./scripts/audio_collect.ps1
   ```

   > Hinweis: Unter Windows PowerShell genügt `./scripts/audio_collect.ps1`.

   Beim ersten Aufruf empfiehlt sich der Zusatz `-WhatIf`, um eine Vorschau der
   Aktionen zu erhalten:

   ```powershell
   pwsh ./scripts/audio_collect.ps1 -WhatIf
   ```

## Optionen

Das Skript akzeptiert optionale Parameter, die Sie bei Bedarf anpassen können:

```powershell
pwsh ./scripts/audio_collect.ps1 -Destination "D:\\MeinOrdner" -Extensions '*.mp3','*.wav'
```

* `-Destination` – Zielordner, in den alle gefundenen Dateien kopiert oder
  verlinkt werden. Standard ist `%USERPROFILE%\Audio_Quelle`.
* `-Extensions` – Liste erlaubter Dateierweiterungen. Standardmäßig werden `mp3`,
  `wav`, `aiff`, `flac`, `aac`, `ogg`, `wma` und `m4a` durchsucht.
* `-TransferMode` – legt fest, ob Dateien kopiert (`Copy`, Standard) oder als
  Hardlink abgelegt werden (`HardLink`).

## Besonderheiten auf dem MacBook und externen Laufwerken

* Das Skript kopiert Dateien – es verschiebt nichts. Damit entspricht es der
  Anforderung „vom MacBook 2011 soll nur kopiert werden“.
* Der Zielordner wird automatisch von der Suche ausgenommen. Wird also z. B.
  `-Destination "/Volumes/T5 EVO/Audio_Quelle"` angegeben, durchsucht das Skript
  diesen Pfad nicht erneut.
* macOS-Laufwerke werden über `/Volumes` erkannt. Alle dort eingebundenen Netzwerk-
  oder USB-Volumes, die Sie im Finder sehen, fließen in die Suche ein.
* Hardlinks sind nur möglich, wenn Quelle und Ziel auf demselben Dateisystem
  liegen. Viele externe SSDs mit exFAT unterstützen keine Hardlinks – in diesem
  Fall fällt das Skript automatisch auf Kopieren zurück.

## iPad und iPhone einbinden

Apple erlaubt keinen direkten Dateizugriff auf iOS-Geräte wie bei einem USB-Stick.
So binden Sie dennoch Audiodateien ein:

1. Öffnen Sie den Finder, wählen Sie Ihr iPhone oder iPad aus und aktivieren Sie
   unter „Dateifreigabe“ die gewünschten Apps. Kopieren Sie deren Dateien in einen
   lokalen Ordner (z. B. `~/Music/Import`).
2. Alternativ können Sie Tools wie [ifuse](https://github.com/libimobiledevice/ifuse)
   nutzen (`brew install ifuse`), um das Gerät als FUSE-Volume nach `/Volumes/<Name>`
   einzubinden. Das Skript durchsucht das eingebundene Volume anschließend wie ein
   gewöhnliches Laufwerk.

Sobald die Dateien lokal oder auf einem gemounteten Volume liegen, sammelt das
Skript sie im Zielordner `Audio_Quelle`.

## Funktionsweise

* Alle Dateisystemlaufwerke (`Get-PSDrive -PSProvider FileSystem`) sowie unter
  macOS erkannte Volumes (`/Volumes/...`) werden rekursiv durchsucht.
* Verzeichnisse, deren Pfad `Ableton` enthält, werden ignoriert.
* Zielpfade erhalten bei Bedarf ein numerisches Suffix (z. B. `Datei (1).wav`),
  sodass bestehende Dateien nicht überschrieben werden – unabhängig davon, ob sie
  kopiert oder verlinkt werden.
* Im Modus `HardLink` wird für Dateien auf demselben Laufwerk ein Hardlink erstellt.
  Liegt Quelle oder Ziel auf unterschiedlichen Laufwerken, fällt das Skript automatisch
  auf Kopieren zurück und informiert über den Grund.

## Hardlinks vs. Kopieren

Hardlinks sind besonders dann hilfreich, wenn Programme wie Traktor oder Apple Music
auf denselben Datenträger zugreifen sollen: Die Musikdatei bleibt nur einmal vorhanden,
alle Hardlinks weisen auf dieselbe physische Datei. Beachten Sie jedoch:

* Hardlinks sind nur innerhalb desselben Laufwerks/Volumes möglich.
* Netzwerkshares oder externe Laufwerke mit anderem Laufwerksbuchstaben bzw.
  anderem Volume-Namen werden deshalb automatisch kopiert.
* Für Hardlinks sind die gleichen Berechtigungen erforderlich wie für gewöhnliche
  Dateien.

Wenn Sie sicherstellen möchten, dass eine Software stets Zugriff auf eine unabhängige
Dateikopie hat (z. B. zur Archivierung oder für Backups), verwenden Sie den
Standardmodus `Copy`.

## Fehlersuche

* Stellen Sie sicher, dass Sie die Ausführungsrichtlinie für Skripte ggf. mit
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` angepasst haben.
* Nutzen Sie den Parameter `-Extensions`, falls Sie zusätzliche Audioformate durchsuchen möchten.
* Verwenden Sie `-Destination`, um den Zielordner auf ein externes Laufwerk oder einen Netzwerkspeicher zu legen.
  Der Ordner wird bei der Suche übersprungen, um Endlosschleifen zu verhindern.
