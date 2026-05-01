#!/usr/bin/env python3
import requests
import json
import os
import logging
import sys
from datetime import datetime, timezone, timedelta
import time
from typing import Optional, Dict, Any, List
from urllib.parse import quote
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

HEADERS = {
    #"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # "Accept": "application/json",
    # "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    # "Accept-Encoding": "gzip, deflate, br",
    # "Referer": "https://www.pathe.fr/",
    # "Origin": "https://www.pathe.fr"
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "cross-site",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}

def fetch_with_retry(url: str, max_retries: int = 3, delay: float = 2.0) -> Optional[requests.Response]:
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 403 and attempt < max_retries - 1:
                logger.warning(f"403 error, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            return response
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"Request failed, retrying in {delay}s... ({e})")
                time.sleep(delay)
            else:
                raise
    return None

def load_env() -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.pathe")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Loaded environment from {env_path}")
    else:
        logger.warning(f"No .env.pathe file found at {env_path}")

def save_config_to_env(city_slug: str, cinema_slugs: List[str]) -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.pathe")
    lines = []
    found_city = False
    found_cinema = False

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    cinema_str = ",".join(cinema_slugs)

    try:
        with open(env_path, "w") as f:
            for line in lines:
                if line.strip().startswith("API_URL="):
                    continue
                elif line.strip().startswith("CITY_SLUG="):
                    f.write(f'CITY_SLUG="{city_slug}"\n')
                    found_city = True
                elif line.strip().startswith("CINEMA_SLUGS="):
                    f.write(f'CINEMA_SLUGS="{cinema_str}"\n')
                    found_cinema = True
                else:
                    f.write(line)
            if not found_city:
                f.write(f'\nCITY_SLUG="{city_slug}"\n')
            if not found_cinema:
                f.write(f'CINEMA_SLUGS="{cinema_str}"\n')
        logger.info(f"Configuration saved to {env_path}")
    except IOError as e:
        logger.error(f"Error saving config to {env_path}: {e}")

def get_cities() -> List[Dict[str, Any]]:
    try:
        response = fetch_with_retry("https://www.pathe.fr/api/cities")
        if response is None:
            return []
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching cities: {e}")
        return []

def configure_city() -> None:
    cities = get_cities()
    if not cities:
        print("Unable to fetch cities list.")
        return

    print("\n=== Configuration Pathe Monitor ===")
    print("Villes disponibles :")
    for i, city in enumerate(cities, 1):
        print(f"{i}. {city['name']} ({city['departement']})")

    while True:
        try:
            choice = input("\nChoisissez une ville (numero) : ")
            idx = int(choice) - 1
            if 0 <= idx < len(cities):
                city = cities[idx]
                city_slug = city['slug']
                cinemas = city.get('cinemas', [])
                break
            else:
                print("Numero invalide, reessayez.")
        except ValueError:
            print("Veuillez entrer un numero valide.")

    print(f"\nCinemas a {city['name']} :")
    for i, cinema in enumerate(cinemas, 1):
        print(f"{i}. {cinema}")

    print("\nQue voulez-vous surveiller ?")
    print("1. Tous les cinemas")
    print("2. Selectionner des cinemas specifiques")

    while True:
        try:
            choice = input("\nChoix (1 ou 2) : ")
            if choice == "1":
                selected_cinemas = cinemas
                break
            elif choice == "2":
                nums = input("Entrez les numeros separes par des espaces (ex: 1 3) : ").split()
                selected_cinemas = []
                for num in nums:
                    idx = int(num) - 1
                    if 0 <= idx < len(cinemas):
                        selected_cinemas.append(cinemas[idx])
                if selected_cinemas:
                    break
                else:
                    print("Aucun cinema selectionne, reessayez.")
            else:
                print("Choix invalide (1 ou 2).")
        except ValueError:
            print("Entree invalide.")

    save_config_to_env(city_slug, selected_cinemas)
    print(f"\nConfiguration sauvegardee !")
    print(f"  Ville : {city['name']}")
    print(f"  Cinemas : {', '.join(selected_cinemas)}")

def validate_env() -> Dict[str, Any]:
    webhook_url = os.getenv("WEBHOOK_URL")
    cinema_slugs_str = os.getenv("CINEMA_SLUGS", "")
    state_file = os.getenv("STATE_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "pathe_movies_state.json"))

    if not webhook_url:
        raise ValueError("WEBHOOK_URL is not set in environment")
    if not cinema_slugs_str:
        raise ValueError("CINEMA_SLUGS is not set. Run with --config to set it.")

    cinema_slugs = [s.strip() for s in cinema_slugs_str.split(",")]

    return {
        'WEBHOOK_URL': webhook_url,
        'STATE_FILE': state_file,
        'EVENT_COLOR': int(os.getenv("EVENT_COLOR", "0x3498DB"), 16),
        'AVP_COLOR': int(os.getenv("AVP_COLOR", "0xFF6B00"), 16),
        'SEANCE_SPECIALE_COLOR': int(os.getenv("SEANCE_SPECIALE_COLOR", "0x9B59B6"), 16),
        'COMING_SOON_COLOR': int(os.getenv("COMING_SOON_COLOR", "0xFFD700"), 16),
        'AVP_FOOTER': os.getenv("AVP_FOOTER", "Pathe - Avant-Premiere"),
        'SEANCE_SPECIALE_FOOTER': os.getenv("SEANCE_SPECIALE_FOOTER", "Pathe - Seance Speciale"),
        'COMING_SOON_FOOTER': os.getenv("COMING_SOON_FOOTER", "Pathe - Prochainement"),
        'NOTIFICATION_DELAY': int(os.getenv("NOTIFICATION_DELAY", "1")),
        'CINEMA_SLUGS': cinema_slugs
    }

def load_state(state_file: str) -> Dict[str, Any]:
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading state file: {e}")
            return {"seen_movies": []}
    return {"seen_movies": []}

def save_state(state: Dict[str, Any], state_file: str) -> None:
    try:
        with open(state_file, "w") as f:
            json.dump(state, f, indent=4)
    except IOError as e:
        logger.error(f"Error saving state file: {e}")

def format_duration(minutes: Optional[int]) -> str:
    if not minutes:
        return "N/A"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h{mins:02d}"
    return f"{mins}min"

def format_datetime(dt_str: Optional[str]) -> str:
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return dt_str

def generate_google_calendar_link(title: str, sales_opening_dt_str: Optional[str], movie_url: Optional[str] = None) -> Optional[str]:
    if not sales_opening_dt_str:
        return None
    try:
        dt = datetime.fromisoformat(sales_opening_dt_str.replace("Z", "+00:00"))
        now_utc = datetime.now(timezone.utc)
        if dt <= now_utc:
            return None
        start_str = dt.strftime("%Y%m%dT%H%M%SZ")
        end_dt = dt + timedelta(minutes=30)
        end_str = end_dt.strftime("%Y%m%dT%H%M%SZ")
        event_title = quote(f"Ouverture ventes: {title}")
        dates_param = f"{start_str}/{end_str}"
        details = f"Ouverture des ventes pour {title}"
        if movie_url:
            details += f"\n{movie_url}"
        details_encoded = quote(details)
        return (
            f"https://calendar.google.com/calendar/render"
            f"?action=TEMPLATE"
            f"&text={event_title}"
            f"&dates={dates_param}"
            f"&details={details_encoded}"
        )
    except (ValueError, TypeError):
        return None


def get_show_details(slug: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://www.pathe.fr/api/show/{slug}?language=fr"
        response = fetch_with_retry(url)
        if response is None:
            return None
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching show details for {slug}: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON for {slug}: {e}")
    return None

def check_avp_tags(show_data: Dict[str, Any]) -> tuple[bool, Optional[str], bool]:
    days = show_data.get("days", {})
    for date, day_info in days.items():
        tags = day_info.get("tags", [])
        tags_lower = [tag.lower() for tag in tags]
        if "avp-equipe" in tags_lower:
            return True, date, True
        if "avp" in tags_lower:
            return True, date, False
    return False, None, False

def check_seancespeciale(show_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    days = show_data.get("days", {})
    for date, day_info in days.items():
        tags = day_info.get("tags", [])
        tags_lower = [tag.lower() for tag in tags]
        if "seancespeciale" in tags_lower:
            return True, date
    return False, None

def send_discord_notification(movie_details: Dict[str, Any], slug: str, config: Dict[str, Any],
                             notification_type: str = "coming_soon", avp_date: Optional[str] = None,
                             is_equipe: bool = False, seance_date: Optional[str] = None,
                             cinemas: Optional[List[str]] = None) -> None:
    title = movie_details.get("title", slug.replace("-", " ").title())
    original_title = movie_details.get("originalTitle", "")

    if original_title and original_title.lower() != title.lower():
        display_title = f"{title} ({original_title})"
    else:
        display_title = title

    duration_min = movie_details.get("duration")
    duration = format_duration(duration_min)

    feelings = movie_details.get("feelings", {})
    wishlist_count = feelings.get("countWishList", 0)

    sales_opening = movie_details.get("salesOpeningDatetime", "")
    sales_opening_formatted = format_datetime(sales_opening)
    google_calendar_link = None

    is_movie = movie_details.get("isMovie", True)

    trailers = movie_details.get("trailers", [])
    trailer_url = None
    for trailer in trailers:
        if trailer.get("isMain", False):
            trailer_url = trailer.get("externalId")
            break

    release_at = movie_details.get("releaseAt", {})
    release_date = release_at.get("FR_FR", "")
    if release_date:
        try:
            dt = datetime.fromisoformat(release_date.replace("Z", "+00:00"))
            release_formatted = dt.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            release_formatted = release_date
    else:
        release_formatted = "N/A"

    if notification_type == "avp" and avp_date:
        try:
            dt = datetime.fromisoformat(avp_date.replace("Z", "+00:00"))
            url_date = dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            url_date = avp_date
        prefix = "films" if is_movie else "evenements"
        movie_url = f"https://www.pathe.fr/{prefix}/{slug}/filters/date-{url_date}"

        if is_equipe:
            embed_title = f"\U0001f3ac {display_title} - Avant-Premiere + Equipe"
        else:
            embed_title = f"\U0001f3ac {display_title} - Avant-Premiere"

        embed_color = config['AVP_COLOR']
        footer_text = config['AVP_FOOTER']
    elif notification_type == "seancespeciale" and seance_date:
        try:
            dt = datetime.fromisoformat(seance_date.replace("Z", "+00:00"))
            url_date = dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            url_date = seance_date
        prefix = "films" if is_movie else "evenements"
        movie_url = f"https://www.pathe.fr/{prefix}/{slug}/filters/date-{url_date}"

        embed_title = f"\U0001f3ea {display_title} - Seance Speciale"
        embed_color = config['SEANCE_SPECIALE_COLOR']
        footer_text = config['SEANCE_SPECIALE_FOOTER']
    else:
        if release_date:
            try:
                dt = datetime.fromisoformat(release_date.replace("Z", "+00:00"))
                url_date = dt.strftime("%Y-%m-%d")
                prefix = "films" if is_movie else "evenements"
                movie_url = f"https://www.pathe.fr/{prefix}/{slug}/filters/date-{url_date}"
            except (ValueError, TypeError):
                prefix = "films" if is_movie else "evenements"
                movie_url = f"https://www.pathe.fr/{prefix}/{slug}"
        else:
            prefix = "films" if is_movie else "evenements"
            movie_url = f"https://www.pathe.fr/{prefix}/{slug}"
        embed_title = f"\U0001f3ac {display_title}"
        embed_color = config['COMING_SOON_COLOR']
        footer_text = config['COMING_SOON_FOOTER']

    if not is_movie and notification_type == "coming_soon":
        embed_color = config['EVENT_COLOR']

    if sales_opening and movie_url:
        google_calendar_link = generate_google_calendar_link(title, sales_opening, movie_url)

    poster_path = movie_details.get("posterPath", {})
    poster = poster_path.get("lg", "") if isinstance(poster_path, dict) else ""

    embed_fields = [
        {"name": "\U0001f4c5 Date de sortie", "value": release_formatted, "inline": True},
        {"name": "\u23f1\ufe0f Duree", "value": duration, "inline": True},
        {"name": "\U0001f39f\ufe0f Ouverture des ventes", "value": sales_opening_formatted, "inline": False},
    ]

    if google_calendar_link:
        embed_fields.append(
            {"name": "\U0001f4c5 Ajouter à Google Calendar", "value": google_calendar_link, "inline": False}
        )

    embed_fields.extend([
        {"name": "\u2764\ufe0f Wishlist", "value": f"{wishlist_count} personne(s)", "inline": True},
        {"name": "\U0001f517 Lien", "value": movie_url, "inline": False}
    ])

    embed = {
        "title": embed_title,
        "url": movie_url,
        "color": embed_color,
        "fields": embed_fields,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": footer_text}
    }

    if trailer_url:
        embed["fields"].append(
            {"name": "\U0001f3a5 Trailer", "value": trailer_url, "inline": False}
        )

    if cinemas:
        cinema_names = [c.replace('cinema-pathe-', '').replace('-', ' ').title() for c in cinemas]
        cinema_field = {"name": "\U0001f3de Cinemas", "value": ", ".join(cinema_names), "inline": False}
        embed["fields"].append(cinema_field)

    if poster:
        embed["thumbnail"] = {"url": poster}

    payload = {"embeds": [embed]}

    try:
        response = requests.post(config['WEBHOOK_URL'], json=payload, timeout=10)
        response.raise_for_status()
        if response.status_code in [200, 204]:
            logger.info(f"Notification sent for {display_title}")
        else:
            logger.warning(f"Unexpected status code: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Error sending Discord notification: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error encoding payload: {e}")

def fetch_all_shows(cinema_slugs: List[str]) -> Dict[str, Any]:
    shows_with_cinema = {}
    for cinema_slug in cinema_slugs:
        try:
            url = f"https://www.pathe.fr/api/cinema/{cinema_slug}/shows?language=fr"
            response = fetch_with_retry(url)
            if response is None:
                logger.error(f"Failed to fetch shows for {cinema_slug} after retries")
                continue
            response.raise_for_status()
            data = response.json()
            shows = data.get("shows", {})
            logger.info(f"Fetched {len(shows)} shows from {cinema_slug}")
            for slug, show_data in shows.items():
                if slug not in shows_with_cinema:
                    shows_with_cinema[slug] = {'data': show_data, 'cinemas': []}
                shows_with_cinema[slug]['cinemas'].append(cinema_slug)
        except requests.RequestException as e:
            logger.error(f"Error fetching shows for {cinema_slug}: {e}")
    return shows_with_cinema

def init_state(cinema_slugs: List[str], state_file: str) -> None:
    logger.info("Initializing state without sending notifications...")
    all_shows = fetch_all_shows(cinema_slugs)
    seen_movies = set()
    for slug, show_info in all_shows.items():
        show_data = show_info['data']
        if not isinstance(show_data, dict):
            continue
        has_avp, _, _ = check_avp_tags(show_data)
        has_seance, _ = check_seancespeciale(show_data)
        is_coming_soon = show_data.get("isComingSoon", False)
        if has_avp:
            seen_movies.add(f"{slug}_avp")
        if has_seance:
            seen_movies.add(f"{slug}_seancespeciale")
        if is_coming_soon and not has_avp and not has_seance:
            seen_movies.add(f"{slug}_coming_soon")
    state = {"seen_movies": list(seen_movies)}
    save_state(state, state_file)
    logger.info(f"State initialized with {len(seen_movies)} movie(s) - no notifications sent")

def main() -> None:
    if "--config" in sys.argv:
        configure_city()
        return

    if "--init-state" in sys.argv:
        load_env()
        config = validate_env()
        init_state(config['CINEMA_SLUGS'], config['STATE_FILE'])
        return

    load_env()
    config = validate_env()

    state = load_state(config['STATE_FILE'])
    seen_movies = set(state.get("seen_movies", []))

    all_shows = fetch_all_shows(config['CINEMA_SLUGS'])
    logger.info(f"Total shows fetched: {len(all_shows)}")

    notified_count = 0

    for slug, show_info in all_shows.items():
        show_data = show_info['data']
        cinemas_for_show = show_info['cinemas']

        if not isinstance(show_data, dict):
            logger.warning(f"Invalid show data for {slug}, skipping")
            continue

        has_avp, avp_date, is_equipe = check_avp_tags(show_data)
        has_seance, seance_date = check_seancespeciale(show_data)
        is_coming_soon = show_data.get("isComingSoon", False)

        if has_avp:
            key = f"{slug}_avp"
            if key not in seen_movies:
                details = get_show_details(slug)
                if details:
                    send_discord_notification(details, slug, config, notification_type="avp",
                                             avp_date=avp_date, is_equipe=is_equipe,
                                             cinemas=cinemas_for_show)
                    seen_movies.add(key)
                    notified_count += 1
                    time.sleep(config['NOTIFICATION_DELAY'])

        if has_seance:
            key = f"{slug}_seancespeciale"
            if key not in seen_movies:
                details = get_show_details(slug)
                if details:
                    send_discord_notification(details, slug, config, notification_type="seancespeciale",
                                             seance_date=seance_date, cinemas=cinemas_for_show)
                    seen_movies.add(key)
                    notified_count += 1
                    time.sleep(config['NOTIFICATION_DELAY'])

        if is_coming_soon and not has_avp and not has_seance:
            key = f"{slug}_coming_soon"
            if key not in seen_movies:
                details = get_show_details(slug)
                if details:
                    send_discord_notification(details, slug, config, notification_type="coming_soon",
                                             cinemas=cinemas_for_show)
                    seen_movies.add(key)
                    notified_count += 1
                    time.sleep(config['NOTIFICATION_DELAY'])

    state["seen_movies"] = list(seen_movies)
    save_state(state, config['STATE_FILE'])

    logger.info(f"Processed {notified_count} new movie(s)")

if __name__ == "__main__":
    main()
