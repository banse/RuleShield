# Hackathon 1-Minute Recording Cheatsheet

## Reihenfolge

1. Opening Card  
   `http://localhost:5174/recording-cards?mode=record&card=opening`  
   3-5 Sekunden stehen lassen.

2. Terminal kurz zeigen  
   `ruleshield init --hermes`  
   `ruleshield start`

3. Hermes Demo aufnehmen  
   `hi`  
   `read README.md and summarize it briefly`  
   `ok thanks`  
   `bye`

4. Optional: Monitor-Übergang  
   `http://localhost:5174/recording-cards?mode=record&card=monitor`

5. Optional: echter Test Monitor  
   `http://localhost:5174/test-monitor`

6. Closing Card  
   `http://localhost:5174/recording-cards?mode=record&card=closing`  
   4-6 Sekunden.

7. End Frame  
   `http://localhost:5174/recording-cards?mode=record&card=end`  
   2-3 Sekunden.

## Nicht vergessen

- GPT-5.1 Mini fuer die Demo verwenden
- keine DevTools oder privaten Tabs sichtbar
- lieber mehrere kurze Takes als ein perfekter One-Take
- wenn der Monitor wackelt, weglassen und nur Hermes + Cards nutzen
