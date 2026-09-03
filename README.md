# SortMyBrick

## Lego-sortering med datorseende (CV)

Ett projekt för att automatiskt sortera LEGO-bitar med hjälp av bildanalys (computer vision) och en manipulator.

## Medlemmar

- Oscar
- Keylan
- Robin
- Aidin

## Delmål

1. Separera enskild bit
2. Skanna bit (identifiera med CV)
3. Flytta biten (placera i rätt magasin)
4. Starta om / återställ för nästa cykel

## Arbetsplan fram till v.50

- v.36–v.38: Förberedelser och krav
  - Bestäm hårdvara (kamera, belysning, sorteringsyta, manipulator)
  - Sätt upp utvecklingsmiljö och versionshantering
  - Samla och märk upp en första dataset med bilder
  - Leverans: lista över vald hårdvara och ett första bilddataset

- v.39–v.41: Prototyp för skanning/identifiering
  - Implementera en första CV-pipeline (t.ex. OpenCV + enkel klassificerare eller transfer learning)
  - Kör experiment på datasetet, utvärdera noggrannhet
  - Leverans: fungerande detektion/klassificering på testbilder

- v.42–v.44: Separationsmekanism
  - Designa och bygg mekanik för att separera enskilda bitar (t.ex. vibrerande matning, kanaler)
  - Iterera för att pålitligt mata fram en bit i taget
  - Leverans: fysisk prototyp som kan framföra en bit i taget till skanningsposition

- v.45–v.47: Manipulator och rörelsestyrning
  - Integrera en manipulator (servo/robotarm) för att plocka och placera
  - Koppla ihop CV-output med rörelseplanering
  - Leverans: system som plockar identifierad bit och placerar i rätt magasin

- v.48–v.49: Integration och robusthetstest
  - Felsökning, robusthetstester och förbättring av felhantering
  - Prestandaoptimering och hantering av kantfall
  - Leverans: stabilt system som klarar kontinuerlig körning under längre period

- v.50: Demo och dokumentation
  - Förbered en demo för presentation
  - Sammanställ dokumentation, instruktionsmanual och framtida förbättringsförslag
  - Leverans: demo och README/konfigurationsguide

## Nästa steg (kort)

1. Bestäm hårdvara och sätt upp miljö (prioritet hög)
2. Börja samla och märka dataset för CV
3. Starta enkel CV-prototyp

---
