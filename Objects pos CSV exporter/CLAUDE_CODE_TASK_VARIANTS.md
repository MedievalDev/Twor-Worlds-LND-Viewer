# Claude Code Task: TW1 Object Exporter — Varianten-Support

## Repository
`https://github.com/MedievalDev/Twor-Worlds-LND-Viewer`
Datei: `tw1_object_exporter.py`

## Aufgabe
Erweitere den Object Exporter um Mesh-Varianten-Support. TW1 speichert in Field 12 der LND-Objekte einen Varianten-Index. Dieser Index bestimmt welche VDF-Datei (3D-Modell) tatsächlich platziert wird. Der Exporter soll den MeshName in der CSV so anpassen, dass er auf das richtige Mesh zeigt.

## Hintergrund
- LND-Objekte haben 14 Felder, Field 12 ist der Varianten-Index
- Beispiel: `TOWER_02_01` mit Field12=2 soll als `TOWER_02_02` in der CSV stehen
- Eine Lookup-Tabelle (`tw1_variant_lookup.csv`) mappt MeshName → VDF-Pattern
- Das Pattern enthält `{V}` wo der Varianten-Index eingesetzt wird

## Lookup-Tabelle Format
```csv
MeshName,VDFPattern,RangeStart,RangeEnd
TOWER_02_01,TOWER_02_0{V},1,3
EN_TREE_09,EN_TREE_09_{V},1,2
EN_STONE_02,EN_STONE_02_{V},1,5
BARREL_01,BARREL_01_{V},1,9
```

## Gewünschtes Verhalten

### Im Exporter:
1. Beim Start die Lookup-Tabelle laden (aus einer Datei neben dem Script, oder eingebettet)
2. Beim Parsen der LND-Objekte Field 12 mitlesen (aktuell wird es übersprungen)
3. Beim CSV-Export:
   - Wenn MeshName in der Lookup-Tabelle vorhanden UND Field12 > 0:
     - Pattern aus Lookup holen (z.B. `TOWER_02_0{V}`)
     - `{V}` durch Field12-Wert ersetzen (z.B. `TOWER_02_02`)
     - Diesen aufgelösten Namen als MeshName in die CSV schreiben
   - Wenn MeshName NICHT in Lookup ODER Field12 == 0:
     - MeshName unverändert in die CSV schreiben (wie bisher)

### Beispiel
LND-Eintrag: `Storeable TOWER_02_01 100 -1 14661 16548 25996 0 152 0 0 100 2 0`
- MeshName = TOWER_02_01
- Field12 = 2
- Lookup: TOWER_02_01 → TOWER_02_0{V}
- Aufgelöst: TOWER_02_0 + 2 = TOWER_02_02
- CSV Output: `TOWER_02_02,14661,16548,25996,0,152,0,100`

### Weiteres Beispiel
LND-Eintrag: `Storeable EN_TREE_09 100 -1 5000 8000 26000 0 100 0 0 100 1 0`
- Field12 = 1
- Lookup: EN_TREE_09 → EN_TREE_09_{V}
- Aufgelöst: EN_TREE_09_1
- CSV Output: `EN_TREE_09_1,5000,8000,26000,0,100,0,100`

### Spezialfall: Field12 = 0
- Einige Objekte haben Field12 = 0
- Wenn Field12 = 0 und MeshName hat keinen Lookup-Eintrag → MeshName unverändert
- Wenn Field12 = 0 und MeshName HAT einen Lookup-Eintrag → setze Field12 = RangeStart aus der Lookup-Tabelle (Default-Variante)

### Spezialfall: Field12 = -1
- Einige Objekte haben Field12 = -1 (z.B. FENCE_03_10 mit -1)
- Behandle wie Field12 = 0 → Default-Variante (RangeStart)

## Wichtige Hinweise
- Die Lookup-Tabelle (`tw1_variant_lookup.csv`) liegt im selben Ordner wie das Script
- GUI: Ein kleiner Hinweis im Status-Bar wie viele Varianten aufgelöst wurden (z.B. "Resolved 1234 variants")
- Field 12 wird nur für die MeshName-Auflösung verwendet, es wird NICHT als eigene Spalte exportiert
- Das CSV-Format bleibt unverändert: `MeshName,X,Y,Z,RotX,RotY,RotZ,Scale` (8 Spalten)
- Die bestehende Funktionalität (Kategorisierung, UE4-Konvertierung) muss weiterhin funktionieren
- Field 12 steht in den LND plaintext objects an Index 12 (0-basiert): `parts[12]`

## Änderungen am Code

### In `extract_objects()`:
- Field 12 mitlesen: `variant = int(parts[12])` 
- Im Object-Dict speichern: `"Variant": variant`
- Aber NICHT in die CSV exportieren

### Neue Funktion `load_variant_lookup(script_dir)`:
- Lädt `tw1_variant_lookup.csv` aus dem Script-Verzeichnis
- Gibt ein Dict zurück: `{mesh_name: {"pattern": "...", "range_start": N, "range_end": M}}`

### Neue Funktion `resolve_variant(mesh_name, variant, lookup)`:
- Wenn mesh_name nicht im lookup → return mesh_name
- Wenn variant <= 0 oder variant == -1 → variant = lookup[mesh_name]["range_start"]
- Pattern holen, {V} ersetzen
- Return aufgelösten Namen

### In `export_csv()` bzw. beim Export:
- Vor dem Schreiben jedes Objekts: `obj["MeshName"] = resolve_variant(obj["MeshName"], obj["Variant"], lookup)`
