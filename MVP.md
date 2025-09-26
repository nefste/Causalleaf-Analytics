**Kurzbericht (Bulletpoints) – Selinas Use-Cases & Visualisierungsidee**

* **Zielbild (GL-Fokus):** Budgettreue und Zielerreichung sicherstellen; strategisch-taktisches Kapazitätsmanagement priorisieren (kein Live-System nötig).
* **Datenrhythmus:** Monatliche oder wöchentliche Exporte genügen (keine Echtzeit).
* **Use Case 1 – Jahres-Kapazitätsplanung:**

  * Bedarf über das Jahr für **Betten, Personal, OP, Sprechstunden, Notfall**.
  * **Interne Faktoren:** retrospektive Klinik-/Prozessdaten (Verweildauer, OP-Zeiten, Patient-Nurse-Ratio, Stationen-Clustering, Ferien/Abwesenheiten, budgetiertes Wachstum).
  * **Externe Faktoren:** z. B. Saisonalität/Epidemien, Wetter, sonstige Treiber.
  * **“Einstellungen”-Panel** zur Parametrisierung (o. g. Faktoren).
* **Use Case 2 – Laufende Prognose & Steuerung:**

  * Monatlich/wöchentlich **erreichte Fallzahlen** ergänzen → **aktualisierte Prognose** des Kapazitätsbedarfs (inkl. interner & externer Faktoren).
  * **Ampelsystem** für Unter-/Überkapazität mit **Entscheidungsvorschlägen** (z. B. OP-Verschiebungen, Personal-Umplanung, Betten öffnen/schließen).
* **Frontend (MVP-Vorschlag):**

  * **Planlinie**: initial geplanter/budgetierter Kapazitätsbedarf pro Tag (Jahresverlauf).
  * **Prognoselinie**: kontinuierliche (wöch./monatl., perspektivisch tgl.) Prognose vs. **verfügbare Kapazität**.
  * **Ampel-Kacheln** je Ressource (Betten/OP/Personal/Ambulanz) + Handlungsempfehlungen.
  * **IKM-KPI** (z. B. Auslastung, Prognosefehler, Wartetage, Stornoquote, Pflege-Engpassindikator).
* **Scope & Skalierung:** Fokus auf **strategisch/taktisch** (hausintern starten), nächster Schritt **kantonale Ebene** (Aggregationen/Überblick).
* **Nächste Schritte (Visualisierung):** Low-fi-Mockup/SVG des Dashboards mit Plan-/Prognosekurve, Ampel-Heatmap und Einstellungen-Panel erstellen – als Diskussionsgrundlage.

*Kontext/Bezug zum Gründungs-Meeting und MVP-Ausrichtung:* 

