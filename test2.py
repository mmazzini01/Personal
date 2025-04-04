import tobii_research as tr
import csv
from datetime import datetime, timedelta



# Trova gli eyetrackers
eyetrackers = tr.find_all_eyetrackers()

if eyetrackers:
    eyetracker = eyetrackers[0]
    print("Trovato eyetracker:", eyetracker.model)

    # Liste per raccogliere i dati
    all_gaze_data = []
    openness_data = []

    # Callback per i dati dello sguardo
    def gaze_data_callback(gaze_data):
        system_time_now = int(datetime.now().timestamp() * 1000)  # Milliseconds
        # Add the current system time to the gaze data
        gaze_data["system_time_now"] = system_time_now  # Store only 
        all_gaze_data.append(gaze_data)
        print("Punto dati raccolto")

    # Callback per il dato di eye openness
    def openness_callback(open_eye):
        openness_data.append(open_eye)

    # Sottoscrizione ai dati dell'eyetracker
    eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
    eyetracker.subscribe_to(tr.EYETRACKER_EYE_OPENNESS_DATA, openness_callback, as_dictionary=True)

    # Aspetta che l'utente voglia terminare la raccolta
    input("Raccolta dati in corso. Premi Invio per terminare e salvare in CSV...")

    # Interrompi la sottoscrizione ai dati
    eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
    eyetracker.unsubscribe_from(tr.EYETRACKER_EYE_OPENNESS_DATA, openness_callback)

    # Nome del file CSV
    filename = "eye_tracking_final.csv"

    # Determina i campi dal primo dato di all_gaze_data
    if all_gaze_data:
        fieldnames = []

        # Ottieni tutte le chiavi del primo elemento (anche nested)
        first_data = all_gaze_data[0]
        for key in first_data.keys():
            if isinstance(first_data[key], dict):  # Se è un dizionario (es. left_eye, right_eye)
                for subkey in first_data[key].keys():
                    fieldnames.append(f"{key}.{subkey}")
            else:
                fieldnames.append(key)

        # Aggiungi le due colonne di openness
        fieldnames.append("left_eye_openness_value")
        fieldnames.append("right_eye_openness_value")

        # Scrivi su CSV
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(fieldnames)  # Scrive l'intestazione

            # Scrive i dati riga per riga
            for i in range(len(all_gaze_data)):  
                row = []
                data_point = all_gaze_data[i]
                openness_point = openness_data[i] if i < len(openness_data) else {"left_eye_openness_value": "", "right_eye_openness_value": ""}

                for field in fieldnames:
                    if field in ["left_eye_openness_value", "right_eye_openness_value"]:
                        row.append(openness_point.get(field, ""))  # Prendi il valore o "" se non c'è
                    elif '.' in field:
                        main_key, sub_key = field.split('.')
                        row.append(data_point[main_key][sub_key])  # Prendi il valore annidato
                    else:
                        row.append(data_point[field])  # Prendi il valore normale
                
                writer.writerow(row)

        print(f"Dati salvati in: {filename}")
        print(f"Totale punti dati raccolti: {len(all_gaze_data)}")

    else:
        print("Nessun dato raccolto.")
else:
    print("Nessun eyetracker trovato.")
