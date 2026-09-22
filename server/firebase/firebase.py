"""
firebase_realtime_handler.py

En klass för att hantera CRUD-operationer och realtidslyssnare
mot Firebase Realtime Database, med hjälp av firebase-admin SDK.

Installation:
    pip install firebase-admin

Förutsättningar:
    - En Firebase-projekt-serviceconto-nyckel (JSON-fil), hämtas från
      Firebase Console > Project Settings > Service Accounts > Generate new private key
    - Databasens URL, t.ex. "https://<ditt-projekt>-default-rtdb.europe-west1.firebasedatabase.app"
"""

import logging
from pathlib import Path
from typing import Any, Callable, Optional

import firebase_admin
from firebase_admin import credentials, db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class FirebaseRealtimeHandler:
    """
    Klass för att hantera anslutning och datahantering mot
    Firebase Realtime Database.
    """

    _app_initialized = False

    def __init__(self, cred_path: str, database_url: str, app_name: str = "[DEFAULT]"):
        """
        Initierar anslutningen till Firebase.

        :param cred_path: Sökväg till service account JSON-nyckel.
        :param database_url: URL till Firebase Realtime Database.
        :param app_name: Namn på Firebase-appinstansen (användbart om flera appar behövs).
        """
        self.cred_path = cred_path
        self.database_url = database_url
        self.app_name = app_name
        self._listeners = {}  # sparar referenser till aktiva lyssnare

        self._initialize_app()

    def _initialize_app(self) -> None:
        """Initierar Firebase-appen om den inte redan är initierad."""
        try:
            # Kontrollera om en app med detta namn redan finns
            self.app = firebase_admin.get_app(self.app_name)
            logger.info(f"Återanvänder existerande Firebase-app: {self.app_name}")
        except ValueError:
            cred = credentials.Certificate(self.cred_path)
            self.app = firebase_admin.initialize_app(
                cred,
                {"databaseURL": self.database_url},
                name=self.app_name,
            )
            logger.info(f"Firebase-app initierad: {self.app_name}")

    def _ref(self, path: str):
        """
        Hjälpmetod som returnerar en referens till en given sökväg
        i databasen, kopplad till rätt app-instans.
        """
        return db.reference(path, app=self.app)

    # ---------------------------
    # CRUD-operationer
    # ---------------------------

    def create(self, path: str, data: dict) -> str:
        """
        Skapar en ny post med auto-genererat ID under given sökväg.

        :param path: Sökväg i databasen, t.ex. "users".
        :param data: Data som ska sparas.
        :return: Det auto-genererade nyckel-ID:t.
        """
        ref = self._ref(path).push(data)
        logger.info(f"Skapade post under '{path}' med id '{ref.key}'")
        return ref.key

    def set(self, path: str, data: Any) -> None:
        """
        Skriver (skriver över) data på en exakt sökväg.

        :param path: Sökväg i databasen, t.ex. "users/user1".
        :param data: Data att spara.
        """
        self._ref(path).set(data)
        logger.info(f"Satte data på '{path}'")

    def update(self, path: str, data: dict) -> None:
        """
        Uppdaterar specifika fält på en given sökväg utan att
        skriva över hela noden.

        :param path: Sökväg i databasen.
        :param data: Dict med fält som ska uppdateras.
        """
        self._ref(path).update(data)
        logger.info(f"Uppdaterade data på '{path}'")

    def read(self, path: str) -> Any:
        """
        Läser data från en given sökväg.

        :param path: Sökväg i databasen.
        :return: Datan på angiven sökväg, eller None om den inte finns.
        """
        data = self._ref(path).get()
        logger.info(f"Läste data från '{path}'")
        return data

    def delete(self, path: str) -> None:
        """
        Tar bort data på en given sökväg.

        :param path: Sökväg i databasen.
        """
        self._ref(path).delete()
        logger.info(f"Tog bort data på '{path}'")

    def query(
        self,
        path: str,
        order_by: str,
        equal_to: Optional[Any] = None,
        start_at: Optional[Any] = None,
        end_at: Optional[Any] = None,
        limit_to_first: Optional[int] = None,
        limit_to_last: Optional[int] = None,
    ) -> Any:
        """
        Utför en query mot en sökväg med filtrering och sortering.

        :param path: Sökväg i databasen.
        :param order_by: Fält att sortera efter, t.ex. "child_key" eller "$key"/"$value".
        :param equal_to: Filtrera på exakt värde.
        :param start_at: Startvärde för intervall.
        :param end_at: Slutvärde för intervall.
        :param limit_to_first: Begränsa till de N första resultaten.
        :param limit_to_last: Begränsa till de N sista resultaten.
        :return: Resultatet av queryn.
        """
        ref = self._ref(path).order_by_child(order_by)

        if equal_to is not None:
            ref = ref.equal_to(equal_to)
        if start_at is not None:
            ref = ref.start_at(start_at)
        if end_at is not None:
            ref = ref.end_at(end_at)
        if limit_to_first is not None:
            ref = ref.limit_to_first(limit_to_first)
        if limit_to_last is not None:
            ref = ref.limit_to_last(limit_to_last)

        result = ref.get()
        logger.info(f"Query utförd på '{path}' (order_by='{order_by}')")
        return result

    # ---------------------------
    # Realtidslyssnare
    # ---------------------------

    def listen(self, path: str, callback: Callable[[Any], None], listener_id: Optional[str] = None) -> str:
        """
        Startar en realtidslyssnare på en given sökväg. Callbacken
        anropas varje gång data ändras.

        :param path: Sökväg att lyssna på.
        :param callback: Funktion som anropas med en firebase_admin.db.Event.
        :param listener_id: Valfritt eget ID för att kunna sluta lyssna senare.
        :return: ID som identifierar lyssnaren (använd för stop_listening).
        """
        ref = self._ref(path)

        def _wrapped_callback(event):
            logger.info(f"Realtidshändelse på '{path}': event_type={event.event_type}, path={event.path}")
            callback(event)

        listener = ref.listen(_wrapped_callback)

        lid = listener_id or path
        self._listeners[lid] = listener
        logger.info(f"Startade lyssnare '{lid}' på '{path}'")
        return lid

    def stop_listening(self, listener_id: str) -> None:
        """
        Stoppar en aktiv realtidslyssnare.

        :param listener_id: ID som returnerades av listen().
        """
        listener = self._listeners.pop(listener_id, None)
        if listener:
            listener.close()
            logger.info(f"Stoppade lyssnare '{listener_id}'")
        else:
            logger.warning(f"Ingen aktiv lyssnare med id '{listener_id}' hittades")

    def stop_all_listeners(self) -> None:
        """Stoppar alla aktiva realtidslyssnare."""
        for lid in list(self._listeners.keys()):
            self.stop_listening(lid)

    # ---------------------------
    # Transaktioner
    # ---------------------------

    def transaction(self, path: str, transaction_update: Callable[[Any], Any]) -> Any:
        """
        Kör en atomisk transaktion på en sökväg, säkerställer att
        uppdateringen sker konsekvent även vid samtidiga skrivningar.

        :param path: Sökväg i databasen.
        :param transaction_update: Funktion som tar emot nuvarande värde
                                    och returnerar det nya värdet.
        :return: Det slutgiltiga värdet efter transaktionen.
        """
        ref = self._ref(path)
        new_value = ref.transaction(transaction_update)
        logger.info(f"Transaktion utförd på '{path}'")
        return new_value


# ---------------------------
# Exempel på användning
# ---------------------------
if __name__ == "__main__":
    # Byt ut mot din egen sökväg och databas-URL
    handler = FirebaseRealtimeHandler(
        cred_path=str(Path(__file__).with_name("sortmybrick-43ef9-firebase-adminsdk-fbsvc-e5d3916f05.json")),
        database_url="",
    )

    # Skapa en ny post
    new_id = handler.create("users", {"name": "Anna", "age": 30})

    # Läsa data
    print(handler.read(f"users/{new_id}"))

    # Uppdatera fält
    handler.update(f"users/{new_id}", {"age": 31})

    # Lyssna på ändringar i realtid
    def on_change(event):
        print(f"Ändring upptäckt: {event.event_type} -> {event.data}")

    handler.listen(f"users/{new_id}", on_change)

    # ... vänta på händelser ...

    # Stäng lyssnare när klart
    handler.stop_all_listeners()

    # Ta bort posten
    handler.delete(f"users/{new_id}")