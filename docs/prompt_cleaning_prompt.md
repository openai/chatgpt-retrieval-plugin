# Prompt-Verbesserung: Bereinigung von Audio-Titeln

## Ursprünglicher Prompt
> Ich möchte eine Bereinigung des Namens und Befreiung von Sonderzeichen und Buchstabensalaten und Zahlen in der Bezeichnung von Audio-Titeln. Es soll eigentlich nur der Titel herausgeschält werden. Und jegliche Tonart und jegliches TrackID und TrackZählen, was im Laufe der Zeit der Datei hinzugefügt wurde, kann gelöscht werden. So dass der Dateiname wieder klar ist. Meistens Track und Interpret.

## Empfohlene Optimierungen
1. **Ziel und gewünschtes Ergebnis präzisieren**  – Definiere klar, dass der bereinigte Dateiname ausschließlich aus „Interpret – Titel“ bestehen soll und nenne Beispiele zulässiger bzw. unerwünschter Elemente.
2. **Formatierungs- und Transformationsregeln strukturieren** – Formuliere Schritt-für-Schritt-Regeln (z. B. Entfernen von Tonarten, Tracknummern und Sonderzeichen), damit das Modell deterministisch vorgehen kann.
3. **Kontext zu Eingabeformat und gewünschten Ausgaben liefern** – Beschreibe das ursprüngliche Dateinamenformat, nenne potentielle Störfaktoren und gib vor, wie die bereinigten Namen auszugeben sind (z. B. Liste, JSON, Tabelle), um die Antwortqualität zu erhöhen.
4. **Beispiele für Vorher/Nachher liefern** – Zeige repräsentative Beispiele, damit das Modell das gewünschte Muster schneller erfasst und konsistente Ergebnisse liefert.

## Varianten
### Variante A – Fokus auf strukturierte Automatisierung
```text
Du arbeitest als Dateibenennungs-Assistent. Bereinige eine Liste von Audio-Dateinamen so, dass ausschließlich das Muster „Interpret – Titel“ übrigbleibt.

Vorgehen:
1. Entferne Präfixe wie Tracknummern (z. B. `01`, `A3`), Disc- oder Mix-Angaben sowie Suffixe wie Tonarten (`in G minor`, `Am`) oder Zählungen (`TrackID`, `Extended Mix`, `Remastered 2010`).
2. Lösche Sonderzeichen, doppelte Leerzeichen und überflüssige Klammern; ersetze `_` oder `.` durch Leerzeichen.
3. Standardisiere die Schreibweise auf „Interpret – Titel“ (Interpret zuerst, dann Titel, jeweils mit korrekter Groß-/Kleinschreibung). Fehlt einer der beiden Bestandteile, gib „Unbekannt“ für das fehlende Element an.

Eingabe: Eine Liste von rohen Dateinamen.
Ausgabe: Eine Markdown-Tabelle mit den Spalten „Originalname“ und „Bereinigter Titel“.

Beispiele:
- `01_artist-name_track-title (Extended Mix).mp3` → `Artist Name – Track Title`
- `B2 The Band - Song Name in F# major.wav` → `The Band – Song Name`
```

### Variante B – Fokus auf kreative Datenaufbereitung
```text
Handle als kreativer Metadaten-Kurator für eine Musikbibliothek. Isoliere aus jedem gelieferten Dateinamen ausschließlich den reinen Songtitel inklusive Interpret im Format „Interpret – Titel“.

Regeln:
- Entferne alles, was nicht direkt zu Interpret oder Songtitel gehört: Tonarten, BPM, Veröffentlichungsjahre, Mix-/Remaster-Hinweise, Track-IDs, Dateiendungen.
- Bereinige Sonderzeichen, setze Leerzeichen korrekt und konvertiere Unterstriche in Leerzeichen.
- Bewahre legitime Bindestriche oder Klammern, wenn sie Teil des Titels sind (z. B. „Love – Live Version“, „(Acoustic)“).

Liefere das Ergebnis als nummerierte Liste im Format `1. Interpret – Titel`.

Beispiel: `03-DJ_Test-Sunrise_in_Am (Remastered 2015).flac` wird zu `1. DJ Test – Sunrise`.
```

### Variante C – Fokus auf technische Skripterstellung
```text
Du hilfst beim Entwickeln eines Skripts zur Bereinigung von Audio-Dateinamen. Analysiere jeden gegebenen Dateinamen und gib strukturierte Anweisungen, wie er in das Format „Interpret – Titel“ konvertiert werden soll.

Für jeden Eintrag soll die Antwort JSON-Objekte mit den Feldern enthalten:
- `original`: ursprünglicher Dateiname
- `steps`: Liste der bereinigungsschritte (z. B. „Remove track number prefix“, „Strip key signature“)
- `result`: finaler Name „Interpret – Titel“

Bereinigungsrichtlinien:
1. Entferne numerische Präfixe, Tonarten, Mix-/Versionstags, Track-IDs, BPM und Jahresangaben.
2. Löse Sonderzeichen ( `_`, `[]`, `()` etc.) auf, lasse jedoch Bindestriche zwischen Interpret und Titel bestehen.
3. Wenn der Interpret nicht eindeutig erkennbar ist, gib `"Unknown Artist"` zurück, behalte den Titel jedoch nach Möglichkeit bei.

Füge zwei eigene Beispiele (Vorher/Nachher + Schritte) hinzu, bevor du die Nutzerliste bearbeitest.
```
