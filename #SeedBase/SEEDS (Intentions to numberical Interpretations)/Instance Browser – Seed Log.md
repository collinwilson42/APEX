# Instance Browser – Seed Log

---

4: 2026-01-30 – Restyle left panel to match right panel + database schema overhaul ^seed-IB-style-db-overhaul

Status: ✅ Complete

Prompts:
- "The database left quadrant needs some serious work. The right side shows a clean neomorphic matte black pallet while the left is blue and gold. The left should match the styling of the right."
- "Also we need a complete redo of the database and api endpoints to match this plus sentiments should also have long text format in the database not just in the front end"

## Tasks Completed

### CSS Overhaul ✅
- [x] Changed left panel from Navy/Gold to Matte Black (#16181c, #0f1012)
- [x] Matched table styling to right panel (databases_database_panels.css):
  - Headers: `rgba(30, 32, 36, 0.98)` gradient
  - Cells: `#c8ccd4` text color
  - Borders: `rgba(255, 255, 255, 0.04-0.08)`
- [x] Updated status badges to matte style (no borders, subtle backgrounds)
- [x] Cell colors now match database.css: Bull #ADEBB3, Bear #3A5F8A
- [x] Alternating row backgrounds with even/odd styling

### Database Schema Updates ✅
- [x] Verified `matrix_bias_label` already exists in sentiment_{id} table
- [x] Verified API endpoints already return `matrix_bias_label`
- [x] instance_database.py has BIAS_LABELS mapping
- [x] Updated JS to display bias label in Sentiments table

### JS Updates ✅
- [x] Added `getBiasLabel()` helper function
- [x] Sentiments table now shows "Strong Bear/Bearish/Neutral/Bullish/Strong Bull"
- [x] Column order: Time, TF, Bias, Composite, Trend, Momentum, Volatility, Volume, Signal, Conf
- [x] Falls back to numeric bias if label not in DB

## Files Modified
- `static/css/apex_instances.css` — V2.5 Matte Black theme
- `static/js/apex_instances.js` — Added getBiasLabel(), updated sentiments table

## Color Palette Applied
| Element | Color | Hex |
|---------|-------|-----|
| Panel Background | Matte Black | #16181c |
| Table Header | Dark Gray Gradient | rgba(30,32,36,0.98) |
| Cell Text | Light Gray | #c8ccd4 |
| Header Text | Medium Gray | #a4a9b3 |
| Border | Subtle White | rgba(255,255,255,0.04-0.08) |
| Bull | Soft Green | #ADEBB3 |
| Bear | Steel Blue | #3A5F8A |
| Neutral | Gray | #A4A9B3 |
