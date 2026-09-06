// Country codes from the server public-domain IANA tzdb zone.tab and aliases.
const CLOCK_COUNTRIES={"Africa/Abidjan": "CI", "Africa/Accra": "GH", "Africa/Addis_Ababa": "ET", "Africa/Algiers": "DZ", "Africa/Asmara": "ER", "Africa/Asmera": "KE", "Africa/Bamako": "ML", "Africa/Bangui": "CF", "Africa/Banjul": "GM", "Africa/Bissau": "GW", "Africa/Blantyre": "MW", "Africa/Brazzaville": "CG", "Africa/Bujumbura": "BI", "Africa/Cairo": "EG", "Africa/Casablanca": "MA", "Africa/Ceuta": "ES", "Africa/Conakry": "GN", "Africa/Dakar": "SN", "Africa/Dar_es_Salaam": "TZ", "Africa/Djibouti": "DJ", "Africa/Douala": "CM", "Africa/El_Aaiun": "EH", "Africa/Freetown": "SL", "Africa/Gaborone": "BW", "Africa/Harare": "ZW", "Africa/Johannesburg": "ZA", "Africa/Juba": "SS", "Africa/Kampala": "UG", "Africa/Khartoum": "SD", "Africa/Kigali": "RW", "Africa/Kinshasa": "CD", "Africa/Lagos": "NG", "Africa/Libreville": "GA", "Africa/Lome": "TG", "Africa/Luanda": "AO", "Africa/Lubumbashi": "CD", "Africa/Lusaka": "ZM", "Africa/Malabo": "GQ", "Africa/Maputo": "MZ", "Africa/Maseru": "LS", "Africa/Mbabane": "SZ", "Africa/Mogadishu": "SO", "Africa/Monrovia": "LR", "Africa/Nairobi": "KE", "Africa/Ndjamena": "TD", "Africa/Niamey": "NE", "Africa/Nouakchott": "MR", "Africa/Ouagadougou": "BF", "Africa/Porto-Novo": "BJ", "Africa/Sao_Tome": "ST", "Africa/Timbuktu": "CI", "Africa/Tripoli": "LY", "Africa/Tunis": "TN", "Africa/Windhoek": "NA", "America/Adak": "US", "America/Anchorage": "US", "America/Anguilla": "AI", "America/Antigua": "AG", "America/Araguaina": "BR", "America/Argentina/Buenos_Aires": "AR", "America/Argentina/Catamarca": "AR", "America/Argentina/ComodRivadavia": "AR", "America/Argentina/Cordoba": "AR", "America/Argentina/Jujuy": "AR", "America/Argentina/La_Rioja": "AR", "America/Argentina/Mendoza": "AR", "America/Argentina/Rio_Gallegos": "AR", "America/Argentina/Salta": "AR", "America/Argentina/San_Juan": "AR", "America/Argentina/San_Luis": "AR", "America/Argentina/Tucuman": "AR", "America/Argentina/Ushuaia": "AR", "America/Aruba": "AW", "America/Asuncion": "PY", "America/Atikokan": "CA", "America/Atka": "US", "America/Bahia": "BR", "America/Bahia_Banderas": "MX", "America/Barbados": "BB", "America/Belem": "BR", "America/Belize": "BZ", "America/Blanc-Sablon": "CA", "America/Boa_Vista": "BR", "America/Bogota": "CO", "America/Boise": "US", "America/Buenos_Aires": "AR", "America/Cambridge_Bay": "CA", "America/Campo_Grande": "BR", "America/Cancun": "MX", "America/Caracas": "VE", "America/Catamarca": "AR", "America/Cayenne": "GF", "America/Cayman": "KY", "America/Chicago": "US", "America/Chihuahua": "MX", "America/Ciudad_Juarez": "MX", "America/Coral_Harbour": "PA", "America/Cordoba": "AR", "America/Costa_Rica": "CR", "America/Coyhaique": "CL", "America/Creston": "CA", "America/Cuiaba": "BR", "America/Curacao": "CW", "America/Danmarkshavn": "GL", "America/Dawson": "CA", "America/Dawson_Creek": "CA", "America/Denver": "US", "America/Detroit": "US", "America/Dominica": "DM", "America/Edmonton": "CA", "America/Eirunepe": "BR", "America/El_Salvador": "SV", "America/Ensenada": "MX", "America/Fort_Nelson": "CA", "America/Fort_Wayne": "US", "America/Fortaleza": "BR", "America/Glace_Bay": "CA", "America/Godthab": "GL", "America/Goose_Bay": "CA", "America/Grand_Turk": "TC", "America/Grenada": "GD", "America/Guadeloupe": "GP", "America/Guatemala": "GT", "America/Guayaquil": "EC", "America/Guyana": "GY", "America/Halifax": "CA", "America/Havana": "CU", "America/Hermosillo": "MX", "America/Indiana/Indianapolis": "US", "America/Indiana/Knox": "US", "America/Indiana/Marengo": "US", "America/Indiana/Petersburg": "US", "America/Indiana/Tell_City": "US", "America/Indiana/Vevay": "US", "America/Indiana/Vincennes": "US", "America/Indiana/Winamac": "US", "America/Indianapolis": "US", "America/Inuvik": "CA", "America/Iqaluit": "CA", "America/Jamaica": "JM", "America/Jujuy": "AR", "America/Juneau": "US", "America/Kentucky/Louisville": "US", "America/Kentucky/Monticello": "US", "America/Knox_IN": "US", "America/Kralendijk": "BQ", "America/La_Paz": "BO", "America/Lima": "PE", "America/Los_Angeles": "US", "America/Louisville": "US", "America/Lower_Princes": "SX", "America/Maceio": "BR", "America/Managua": "NI", "America/Manaus": "BR", "America/Marigot": "MF", "America/Martinique": "MQ", "America/Matamoros": "MX", "America/Mazatlan": "MX", "America/Mendoza": "AR", "America/Menominee": "US", "America/Merida": "MX", "America/Metlakatla": "US", "America/Mexico_City": "MX", "America/Miquelon": "PM", "America/Moncton": "CA", "America/Monterrey": "MX", "America/Montevideo": "UY", "America/Montreal": "CA", "America/Montserrat": "MS", "America/Nassau": "BS", "America/New_York": "US", "America/Nipigon": "CA", "America/Nome": "US", "America/Noronha": "BR", "America/North_Dakota/Beulah": "US", "America/North_Dakota/Center": "US", "America/North_Dakota/New_Salem": "US", "America/Nuuk": "GL", "America/Ojinaga": "MX", "America/Panama": "PA", "America/Pangnirtung": "CA", "America/Paramaribo": "SR", "America/Phoenix": "US", "America/Port-au-Prince": "HT", "America/Port_of_Spain": "TT", "America/Porto_Acre": "BR", "America/Porto_Velho": "BR", "America/Puerto_Rico": "PR", "America/Punta_Arenas": "CL", "America/Rainy_River": "CA", "America/Rankin_Inlet": "CA", "America/Recife": "BR", "America/Regina": "CA", "America/Resolute": "CA", "America/Rio_Branco": "BR", "America/Rosario": "AR", "America/Santa_Isabel": "MX", "America/Santarem": "BR", "America/Santiago": "CL", "America/Santo_Domingo": "DO", "America/Sao_Paulo": "BR", "America/Scoresbysund": "GL", "America/Shiprock": "US", "America/Sitka": "US", "America/St_Barthelemy": "BL", "America/St_Johns": "CA", "America/St_Kitts": "KN", "America/St_Lucia": "LC", "America/St_Thomas": "VI", "America/St_Vincent": "VC", "America/Swift_Current": "CA", "America/Tegucigalpa": "HN", "America/Thule": "GL", "America/Thunder_Bay": "CA", "America/Tijuana": "MX", "America/Toronto": "CA", "America/Tortola": "VG", "America/Vancouver": "CA", "America/Virgin": "PR", "America/Whitehorse": "CA", "America/Winnipeg": "CA", "America/Yakutat": "US", "America/Yellowknife": "CA", "Antarctica/Casey": "AQ", "Antarctica/Davis": "AQ", "Antarctica/DumontDUrville": "AQ", "Antarctica/Macquarie": "AU", "Antarctica/Mawson": "AQ", "Antarctica/McMurdo": "AQ", "Antarctica/Palmer": "AQ", "Antarctica/Rothera": "AQ", "Antarctica/South_Pole": "NZ", "Antarctica/Syowa": "AQ", "Antarctica/Troll": "AQ", "Antarctica/Vostok": "AQ", "Arctic/Longyearbyen": "SJ", "Asia/Aden": "YE", "Asia/Almaty": "KZ", "Asia/Amman": "JO", "Asia/Anadyr": "RU", "Asia/Aqtau": "KZ", "Asia/Aqtobe": "KZ", "Asia/Ashgabat": "TM", "Asia/Ashkhabad": "TM", "Asia/Atyrau": "KZ", "Asia/Baghdad": "IQ", "Asia/Bahrain": "BH", "Asia/Baku": "AZ", "Asia/Bangkok": "TH", "Asia/Barnaul": "RU", "Asia/Beirut": "LB", "Asia/Bishkek": "KG", "Asia/Brunei": "BN", "Asia/Calcutta": "IN", "Asia/Chita": "RU", "Asia/Choibalsan": "MN", "Asia/Chongqing": "CN", "Asia/Chungking": "CN", "Asia/Colombo": "LK", "Asia/Dacca": "BD", "Asia/Damascus": "SY", "Asia/Dhaka": "BD", "Asia/Dili": "TL", "Asia/Dubai": "AE", "Asia/Dushanbe": "TJ", "Asia/Famagusta": "CY", "Asia/Gaza": "PS", "Asia/Harbin": "CN", "Asia/Hebron": "PS", "Asia/Ho_Chi_Minh": "VN", "Asia/Hong_Kong": "HK", "Asia/Hovd": "MN", "Asia/Irkutsk": "RU", "Asia/Istanbul": "TR", "Asia/Jakarta": "ID", "Asia/Jayapura": "ID", "Asia/Jerusalem": "IL", "Asia/Kabul": "AF", "Asia/Kamchatka": "RU", "Asia/Karachi": "PK", "Asia/Kashgar": "CN", "Asia/Kathmandu": "NP", "Asia/Katmandu": "NP", "Asia/Khandyga": "RU", "Asia/Kolkata": "IN", "Asia/Krasnoyarsk": "RU", "Asia/Kuala_Lumpur": "MY", "Asia/Kuching": "MY", "Asia/Kuwait": "KW", "Asia/Macao": "MO", "Asia/Macau": "MO", "Asia/Magadan": "RU", "Asia/Makassar": "ID", "Asia/Manila": "PH", "Asia/Muscat": "OM", "Asia/Nicosia": "CY", "Asia/Novokuznetsk": "RU", "Asia/Novosibirsk": "RU", "Asia/Omsk": "RU", "Asia/Oral": "KZ", "Asia/Phnom_Penh": "KH", "Asia/Pontianak": "ID", "Asia/Pyongyang": "KP", "Asia/Qatar": "QA", "Asia/Qostanay": "KZ", "Asia/Qyzylorda": "KZ", "Asia/Rangoon": "MM", "Asia/Riyadh": "SA", "Asia/Saigon": "VN", "Asia/Sakhalin": "RU", "Asia/Samarkand": "UZ", "Asia/Seoul": "KR", "Asia/Shanghai": "CN", "Asia/Singapore": "SG", "Asia/Srednekolymsk": "RU", "Asia/Taipei": "TW", "Asia/Tashkent": "UZ", "Asia/Tbilisi": "GE", "Asia/Tehran": "IR", "Asia/Tel_Aviv": "IL", "Asia/Thimbu": "BT", "Asia/Thimphu": "BT", "Asia/Tokyo": "JP", "Asia/Tomsk": "RU", "Asia/Ujung_Pandang": "ID", "Asia/Ulaanbaatar": "MN", "Asia/Ulan_Bator": "MN", "Asia/Urumqi": "CN", "Asia/Ust-Nera": "RU", "Asia/Vientiane": "LA", "Asia/Vladivostok": "RU", "Asia/Yakutsk": "RU", "Asia/Yangon": "MM", "Asia/Yekaterinburg": "RU", "Asia/Yerevan": "AM", "Atlantic/Azores": "PT", "Atlantic/Bermuda": "BM", "Atlantic/Canary": "ES", "Atlantic/Cape_Verde": "CV", "Atlantic/Faeroe": "FO", "Atlantic/Faroe": "FO", "Atlantic/Jan_Mayen": "DE", "Atlantic/Madeira": "PT", "Atlantic/Reykjavik": "IS", "Atlantic/South_Georgia": "GS", "Atlantic/St_Helena": "SH", "Atlantic/Stanley": "FK", "Australia/ACT": "AU", "Australia/Adelaide": "AU", "Australia/Brisbane": "AU", "Australia/Broken_Hill": "AU", "Australia/Canberra": "AU", "Australia/Currie": "AU", "Australia/Darwin": "AU", "Australia/Eucla": "AU", "Australia/Hobart": "AU", "Australia/LHI": "AU", "Australia/Lindeman": "AU", "Australia/Lord_Howe": "AU", "Australia/Melbourne": "AU", "Australia/NSW": "AU", "Australia/North": "AU", "Australia/Perth": "AU", "Australia/Queensland": "AU", "Australia/South": "AU", "Australia/Sydney": "AU", "Australia/Tasmania": "AU", "Australia/Victoria": "AU", "Australia/West": "AU", "Australia/Yancowinna": "AU", "Brazil/Acre": "BR", "Brazil/DeNoronha": "BR", "Brazil/East": "BR", "Brazil/West": "BR", "Canada/Atlantic": "CA", "Canada/Central": "CA", "Canada/Eastern": "CA", "Canada/Mountain": "CA", "Canada/Newfoundland": "CA", "Canada/Pacific": "CA", "Canada/Saskatchewan": "CA", "Canada/Yukon": "CA", "Chile/Continental": "CL", "Chile/EasterIsland": "CL", "Cuba": "CU", "Egypt": "EG", "Eire": "IE", "Europe/Amsterdam": "NL", "Europe/Andorra": "AD", "Europe/Astrakhan": "RU", "Europe/Athens": "GR", "Europe/Belfast": "GB", "Europe/Belgrade": "RS", "Europe/Berlin": "DE", "Europe/Bratislava": "SK", "Europe/Brussels": "BE", "Europe/Bucharest": "RO", "Europe/Budapest": "HU", "Europe/Busingen": "DE", "Europe/Chisinau": "MD", "Europe/Copenhagen": "DK", "Europe/Dublin": "IE", "Europe/Gibraltar": "GI", "Europe/Guernsey": "GG", "Europe/Helsinki": "FI", "Europe/Isle_of_Man": "IM", "Europe/Istanbul": "TR", "Europe/Jersey": "JE", "Europe/Kaliningrad": "RU", "Europe/Kiev": "UA", "Europe/Kirov": "RU", "Europe/Kyiv": "UA", "Europe/Lisbon": "PT", "Europe/Ljubljana": "SI", "Europe/London": "GB", "Europe/Luxembourg": "LU", "Europe/Madrid": "ES", "Europe/Malta": "MT", "Europe/Mariehamn": "AX", "Europe/Minsk": "BY", "Europe/Monaco": "MC", "Europe/Moscow": "RU", "Europe/Nicosia": "CY", "Europe/Oslo": "NO", "Europe/Paris": "FR", "Europe/Podgorica": "ME", "Europe/Prague": "CZ", "Europe/Riga": "LV", "Europe/Rome": "IT", "Europe/Samara": "RU", "Europe/San_Marino": "SM", "Europe/Sarajevo": "BA", "Europe/Saratov": "RU", "Europe/Simferopol": "UA", "Europe/Skopje": "MK", "Europe/Sofia": "BG", "Europe/Stockholm": "SE", "Europe/Tallinn": "EE", "Europe/Tirane": "AL", "Europe/Tiraspol": "MD", "Europe/Ulyanovsk": "RU", "Europe/Uzhgorod": "UA", "Europe/Vaduz": "LI", "Europe/Vatican": "VA", "Europe/Vienna": "AT", "Europe/Vilnius": "LT", "Europe/Volgograd": "RU", "Europe/Warsaw": "PL", "Europe/Zagreb": "HR", "Europe/Zaporozhye": "UA", "Europe/Zurich": "CH", "GB": "GB", "GB-Eire": "GB", "Hongkong": "HK", "Iceland": "CI", "Indian/Antananarivo": "MG", "Indian/Chagos": "IO", "Indian/Christmas": "CX", "Indian/Cocos": "CC", "Indian/Comoro": "KM", "Indian/Kerguelen": "TF", "Indian/Mahe": "SC", "Indian/Maldives": "MV", "Indian/Mauritius": "MU", "Indian/Mayotte": "YT", "Indian/Reunion": "RE", "Iran": "IR", "Israel": "IL", "Jamaica": "JM", "Japan": "JP", "Kwajalein": "MH", "Libya": "LY", "Mexico/BajaNorte": "MX", "Mexico/BajaSur": "MX", "Mexico/General": "MX", "NZ": "NZ", "NZ-CHAT": "NZ", "Navajo": "US", "PRC": "CN", "Pacific/Apia": "WS", "Pacific/Auckland": "NZ", "Pacific/Bougainville": "PG", "Pacific/Chatham": "NZ", "Pacific/Chuuk": "FM", "Pacific/Easter": "CL", "Pacific/Efate": "VU", "Pacific/Enderbury": "KI", "Pacific/Fakaofo": "TK", "Pacific/Fiji": "FJ", "Pacific/Funafuti": "TV", "Pacific/Galapagos": "EC", "Pacific/Gambier": "PF", "Pacific/Guadalcanal": "SB", "Pacific/Guam": "GU", "Pacific/Honolulu": "US", "Pacific/Johnston": "US", "Pacific/Kanton": "KI", "Pacific/Kiritimati": "KI", "Pacific/Kosrae": "FM", "Pacific/Kwajalein": "MH", "Pacific/Majuro": "MH", "Pacific/Marquesas": "PF", "Pacific/Midway": "UM", "Pacific/Nauru": "NR", "Pacific/Niue": "NU", "Pacific/Norfolk": "NF", "Pacific/Noumea": "NC", "Pacific/Pago_Pago": "AS", "Pacific/Palau": "PW", "Pacific/Pitcairn": "PN", "Pacific/Pohnpei": "FM", "Pacific/Ponape": "SB", "Pacific/Port_Moresby": "PG", "Pacific/Rarotonga": "CK", "Pacific/Saipan": "MP", "Pacific/Samoa": "AS", "Pacific/Tahiti": "PF", "Pacific/Tarawa": "KI", "Pacific/Tongatapu": "TO", "Pacific/Truk": "PG", "Pacific/Wake": "UM", "Pacific/Wallis": "WF", "Pacific/Yap": "PG", "Poland": "PL", "Portugal": "PT", "ROC": "TW", "ROK": "KR", "Singapore": "SG", "Turkey": "TR", "US/Alaska": "US", "US/Aleutian": "US", "US/Arizona": "US", "US/Central": "US", "US/East-Indiana": "US", "US/Eastern": "US", "US/Hawaii": "US", "US/Indiana-Starke": "US", "US/Michigan": "US", "US/Mountain": "US", "US/Pacific": "US", "US/Samoa": "AS", "W-SU": "RU"};
function clockCountry(zone) { return CLOCK_COUNTRIES[zone] ? new Intl.DisplayNames(["en"],{type:"region"}).of(CLOCK_COUNTRIES[zone]) : ""; }
"use strict";

const REFRESH_INTERVAL = 5000;

const NTP_SYNC_INTERVAL = 30000;

let WARNING_DROPS=1, CRITICAL_DROPS=10;
let WARNING_LAST_SEEN =
    10 * 60;

let CRITICAL_LAST_SEEN =
    60 * 60;


const DEFAULT_TIMEZONES = [
    {
        name: "New York",
        zone: "America/New_York",
    },
    {
        name: "London",
        zone: "Europe/London",
    },
    {
        name: "Paris",
        zone: "Europe/Paris",
    },
    {
        name: "Tel Aviv",
        zone: "Asia/Jerusalem",
    },
    {
        name: "Tokyo",
        zone: "Asia/Tokyo",
    },
    {
        name: "Sydney",
        zone: "Australia/Sydney",
    },
];


let clients = [];

let ntpBaseTimestamp = null;
let ntpBasePerformance = null;


function stored(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
function persist(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; } }
let TIMEZONES = stored("ntp_clocks", DEFAULT_TIMEZONES);
if (!Array.isArray(TIMEZONES)) TIMEZONES = DEFAULT_TIMEZONES;
TIMEZONES = TIMEZONES.filter(item => { try { new Intl.DateTimeFormat("en", {timeZone:item.zone}); return typeof item.name === "string"; } catch { return false; } });
let settings = stored("ntp_settings", {location:"London",latitude:51.5074,longitude:-0.1278});
if (!settings || !Number.isFinite(settings.latitude) || !Number.isFinite(settings.longitude)) settings = {location:"London",latitude:51.5074,longitude:-0.1278};
let openCards = new Set();

function escapeHtml(value) {
    return String(
        value ?? ""
    )
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


function saveOpenCards() {
    localStorage.setItem(
        "ntp_open_cards",
        JSON.stringify(
            [...openCards]
        )
    );
}


function parseInteger(value) {
    const number =
        Number.parseInt(
            value,
            10
        );

    return Number.isNaN(number)
        ? null
        : number;
}


function lastSeenSeconds(value) {

    if (!value) {
        return null;
    }

    const raw =
        String(value)
            .trim()
            .toLowerCase();

    if (
        raw === "-" ||
        raw === "?" ||
        raw === ""
    ) {
        return null;
    }

    if (/^\d+$/.test(raw)) {
        return Number.parseInt(
            raw,
            10
        );
    }

    const match =
        raw.match(
            /^(\d+(?:\.\d+)?)\s*([a-z]+)$/i
        );

    if (!match) {
        return null;
    }

    const number =
        Number.parseFloat(
            match[1]
        );

    const unit =
        match[2];

    if (
        [
            "s",
            "sec",
            "secs",
            "second",
            "seconds",
        ].includes(unit)
    ) {
        return number;
    }

    if (
        [
            "m",
            "min",
            "mins",
            "minute",
            "minutes",
        ].includes(unit)
    ) {
        return number * 60;
    }

    if (
        [
            "h",
            "hr",
            "hrs",
            "hour",
            "hours",
        ].includes(unit)
    ) {
        return number * 3600;
    }

    if (
        [
            "d",
            "day",
            "days",
        ].includes(unit)
    ) {
        return number * 86400;
    }

    return null;
}


function humanLastSeen(value) {

    const seconds =
        lastSeenSeconds(value);

    if (seconds === null) {
        return value || "Unknown";
    }

    if (seconds < 60) {
        return `${
            Math.floor(seconds)
        } sec ago`;
    }

    if (seconds < 3600) {
        return `${
            Math.floor(
                seconds / 60
            )
        } min ago`;
    }

    if (seconds < 86400) {
        return `${
            Math.floor(
                seconds / 3600
            )
        } hr ago`;
    }

    return `${
        Math.floor(
            seconds / 86400
        )
    } d ago`;
}


function severity(client) {

    const drops =
        parseInteger(
            client.Drop
        );

    const last =
        lastSeenSeconds(
            client.Last
        );

    if (
        drops === null ||
        last === null
    ) {
        return "unknown";
    }

    if (
        drops >= CRITICAL_DROPS ||
        last >=
            CRITICAL_LAST_SEEN
    ) {
        return "critical";
    }

    if (
        drops >= WARNING_DROPS ||
        last >=
            WARNING_LAST_SEEN
    ) {
        return "warning";
    }

    return "ok";
}


function renderClient(client) {

    const address =
        client.addr || "";

    const title = client.hostname || address;

    const state =
        severity(client);

    const open =
        openCards.has(
            address
        );

    const card =
        document.createElement(
            "article"
        );

    card.className =
        `ui segment client-card${
            open
                ? " open"
                : ""
        }`;

    card.dataset.address =
        address;

    card.innerHTML = `
        <div class="client-head ${state}">
            <span
                class="client-address"
                title="${escapeHtml(title)}"
            >
                ${escapeHtml(title)}
                ${client.hostname ? `<small class="client-ip">${escapeHtml(address)}</small>` : ""}
            </span>

            <span class="caret">
                ${open ? "▲" : "▼"}
            </span>
        </div>

        <div class="client-body">

            <div class="detail">
                <span class="detail-label">
                    NTP Packets
                </span>

                <span>
                    ${escapeHtml(
                        client.NTP || "-"
                    )}
                </span>
            </div>

            <div class="detail">
                <span class="detail-label">
                    Dropped Packets
                </span>

                <span>
                    ${escapeHtml(
                        client.Drop || "-"
                    )}
                </span>
            </div>

            <div class="detail">
                <span class="detail-label">
                    Command Packets
                </span>

                <span>
                    ${escapeHtml(
                        client.Cmd || "-"
                    )}
                </span>
            </div>

            <div class="detail">
                <span class="detail-label">
                    Interval
                </span>

                <span>
                    ${escapeHtml(
                        client.Int || "-"
                    )}
                </span>
            </div>

            <div class="detail">
                <span class="detail-label">
                    Last Seen
                </span>

                <span>
                    ${escapeHtml(
                        humanLastSeen(
                            client.Last
                        )
                    )}
                </span>
            </div>

        </div>
    `;

    card
        .querySelector(
            ".client-head"
        )
        .addEventListener(
            "click",
            () => {
                card.classList.toggle(
                    "open"
                );

                const isOpen =
                    card.classList.contains(
                        "open"
                    );

                card.querySelector(
                    ".caret"
                ).textContent =
                    isOpen
                        ? "▲"
                        : "▼";

                if (isOpen) {
                    openCards.add(
                        address
                    );
                }
                else {
                    openCards.delete(
                        address
                    );
                }

                saveOpenCards();

                updateExpandToggle();
            }
        );

    return card;
}


function updateSummary(rows) {

    const counts = {
        ok: 0,
        warning: 0,
        critical: 0,
        unknown: 0,
    };

    rows.forEach(
        client => {
            counts[
                severity(client)
            ]++;
        }
    );

    document.getElementById(
        "clients-count"
    ).textContent =
        rows.length;

    document.getElementById(
        "count-ok"
    ).textContent =
        counts.ok;

    document.getElementById(
        "count-warning"
    ).textContent =
        counts.warning;

    document.getElementById(
        "count-critical"
    ).textContent =
        counts.critical;

    document.getElementById(
        "count-unknown"
    ).textContent =
        counts.unknown;
}


function sortClients(rows) {

    const mode =
        document.getElementById(
            "sort-select"
        ).value;

    const copy =
        [...rows];

    if (mode === "drop") {

        copy.sort(
            (a, b) =>
                (
                    parseInteger(
                        b.Drop
                    ) ?? -1
                )
                -
                (
                    parseInteger(
                        a.Drop
                    ) ?? -1
                )
        );
    }

    else if (
        mode === "last"
    ) {

        copy.sort(
            (a, b) =>
                (
                    lastSeenSeconds(
                        a.Last
                    ) ?? Infinity
                )
                -
                (
                    lastSeenSeconds(
                        b.Last
                    ) ?? Infinity
                )
        );
    }

    else {

        copy.sort(
            (a, b) =>
                (
                    a.addr || ""
                ).localeCompare(
                    b.addr || "",
                    undefined,
                    {
                        numeric: true,
                        sensitivity:
                            "base",
                    }
                )
        );
    }

    return copy;
}


function renderClients() {

    const query =
        document
            .getElementById(
                "search"
            )
            .value
            .trim()
            .toLowerCase();

    let rows =
        clients.filter(
            client => {

                if (!query) {
                    return true;
                }

                return Object.values(
                    client
                )
                    .join(" ")
                    .toLowerCase()
                    .includes(
                        query
                    );
            }
        );

    rows =
        sortClients(rows);

    updateSummary(
        rows
    );

    const grid =
        document.getElementById(
            "client-grid"
        );

    grid.replaceChildren(
        ...rows.map(
            renderClient
        )
    );

    updateExpandToggle();
}


function updateExpandToggle() {
    const panels=[...document.querySelectorAll("main details")];
    const cards=[...document.querySelectorAll(".client-card")];
    const toggle=document.getElementById("expand-toggle");
    const states=[...panels.map(p=>p.open),...cards.map(c=>c.classList.contains("open"))];
    toggle.checked=states.length>0 && states.every(Boolean);
    toggle.indeterminate=states.some(Boolean) && !toggle.checked;
}

function showError(message) {

    const banner =
        document.getElementById(
            "error-banner"
        );

    banner.textContent =
        message;

    banner.classList.remove(
        "hidden"
    );
}


function hideError() {

    document
        .getElementById(
            "error-banner"
        )
        .classList.add(
            "hidden"
        );
}


function setServerStatus(
    state,
    message
) {

    document.getElementById(
        "status-dot"
    ).className =
        `status-dot ${state}`;

    document.getElementById(
        "server-status"
    ).textContent =
        message;
}


async function refreshTracking() {

    const response =
        await fetch(
            "/dashboard/tracking",
            {
                cache:
                    "no-store",
            }
        );

    const payload =
        await response.json();

    if (
        payload.status !== "ok"
    ) {
        throw new Error(
            payload.error ||
            "Chrony tracking unavailable"
        );
    }

    const tracking =
        payload.tracking;

    document.getElementById(
        "stratum"
    ).textContent =
        tracking.Stratum || "-";

    document.getElementById(
        "reference-id"
    ).textContent =
        tracking[
            "Reference ID"
        ] || "-";

    document.getElementById(
        "last-offset"
    ).textContent =
        tracking[
            "Last offset"
        ] || "-";

    document.getElementById(
        "rms-offset"
    ).textContent =
        tracking[
            "RMS offset"
        ] || "-";

    document.getElementById(
        "leap-status"
    ).textContent =
        tracking[
            "Leap status"
        ] || "-";
}


async function refreshClients() {

    const response =
        await fetch(
            "/dashboard/clients",
            {
                cache:
                    "no-store",
            }
        );

    const payload =
        await response.json();

    if (
        payload.status !== "ok"
    ) {
        throw new Error(
            payload.error ||
            "Chrony clients unavailable"
        );
    }

    applyClientColours(payload.colours);
    if(payload.thresholds){WARNING_LAST_SEEN=payload.thresholds.warning_seconds;CRITICAL_LAST_SEEN=payload.thresholds.critical_seconds;WARNING_DROPS=payload.thresholds.warning_drops;CRITICAL_DROPS=payload.thresholds.critical_drops;}
    clients =
        payload.clients || [];

    document.getElementById(
        "last-refresh"
    ).textContent =
        new Date(
            payload.timestamp
        ).toLocaleString();

    renderClients();
    if(payload.summary) {
        const ids={total_clients_seen:"clients-count",total_healthy:"count-ok",total_warning:"count-warning",total_critical:"count-critical",total_unknown:"count-unknown"};
        for(const [key,id] of Object.entries(ids))document.getElementById(id).textContent=payload.summary[key];
    }
}


async function synchroniseNtpClock() {

    const response =
        await fetch(
            "/dashboard/time",
            {
                cache:
                    "no-store",
            }
        );

    const payload =
        await response.json();

    if (
        payload.status !== "ok"
    ) {
        throw new Error(
            payload.error ||
            "NTP service unavailable"
        );
    }

    ntpBaseTimestamp =
        payload.timestamp * 1000;

    ntpBasePerformance =
        performance.now();

    document.getElementById(
        "ntp-rtt"
    ).textContent =
        `${payload.round_trip_ms} ms`;
}


function currentNtpDate() {

    if (
        ntpBaseTimestamp === null ||
        ntpBasePerformance === null
    ) {
        return null;
    }

    const elapsed =
        performance.now()
        -
        ntpBasePerformance;

    if (elapsed > 90000) return null;

    return new Date(
        ntpBaseTimestamp
        +
        elapsed
    );
}


function buildClocks() {

    const container =
        document.getElementById(
            "clocks"
        );

    container.replaceChildren(
        ...TIMEZONES.map(
            item => {

                const card =
                    document.createElement(
                        "div"
                    );

                card.className =
                    "ui segment clock-card";

                card.innerHTML = `
                    <div class="clock-city">
                        ${escapeHtml(
                            item.name
                        )}
                    </div>

                    <div class="clock-zone">
                        ${escapeHtml(clockCountry(item.zone))}
                    </div>

                    <div
                        class="clock-time"
                        data-zone="${escapeHtml(
                            item.zone
                        )}"
                    >
                        --:--:--
                    </div>

                    <div
                        class="clock-date"
                        data-date-zone="${escapeHtml(
                            item.zone
                        )}"
                    >
                        --
                    </div>
                `;

                const country = CLOCK_COUNTRIES[item.zone];
                if (country) {
                    const flag = document.createElement("i");
                    flag.className = country.toLowerCase() + " flag";
                    flag.setAttribute("aria-hidden", "true");
                    card.querySelector(".clock-zone").prepend(flag);
                }

                const remove = document.createElement("button");
                remove.type="button"; remove.className="clock-remove";
                remove.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6L18 18M18 6L6 18"/></svg>';
                remove.setAttribute("aria-label", "Remove "+item.name+" clock");
                remove.addEventListener("click", async () => {
                    remove.disabled=true;
                    try {await saveSharedSettings({clocks:TIMEZONES.filter(c=>c.zone!==item.zone)});}
                    catch(error){document.getElementById("clock-feedback").textContent=error.message;remove.disabled=false;}
                });
                const offset=document.createElement("div"); offset.className="clock-offset";
                offset.dataset.offsetZone=item.zone; card.append(offset);
                if(settings.clock_backgrounds)queueMicrotask(()=>loadCityBackground(card,item));
                return card;
            }
        )
    );
}


async function loadCityBackground(card,item) {
    try {
        const {image:photo}=await accessRequest("/dashboard/clocks/image?zone="+encodeURIComponent(item.zone));
        if(!photo || !card.isConnected || !settings.clock_backgrounds)return;
        const image=document.createElement("img");image.className="clock-city-background";image.alt="";image.setAttribute("aria-hidden","true");image.loading="lazy";image.referrerPolicy="no-referrer";
        const credit=uiButton("ⓘ",()=>showCityPhotoCredit(photo));credit.className="ui icon button clock-photo-credit";credit.setAttribute("aria-label","Photo Credit for "+item.name);credit.title="Photo Credit";credit.hidden=true;
        image.onload=()=>{credit.hidden=false;};image.onerror=()=>{image.remove();credit.remove();};image.src=photo.image_url;card.prepend(image);card.append(credit);
    } catch { /* Photos are optional; clocks remain usable when imagery is unavailable. */ }
}
function showCityPhotoCredit(photo) {
    const dialog=document.getElementById("city-photo-dialog"),content=document.getElementById("city-photo-content");content.replaceChildren();
    for(const text of [photo.city,photo.artist,photo.credit,photo.license])if(text){const p=document.createElement("p");p.textContent=text;content.append(p);}
    const link=document.createElement("a");link.href=photo.source_url;link.textContent="Original photograph and licence on Wikimedia Commons";link.target="_blank";link.rel="noopener noreferrer";content.append(link);
    dialog.showModal();
}

function updateClocks() {

    const date =
        currentNtpDate();

    if (!date) {
        document.querySelectorAll(".clock-time").forEach(el => {el.textContent = "Unavailable";});
        return;
    }

    document.querySelectorAll("[data-offset-zone]").forEach(el => {
        const part=new Intl.DateTimeFormat("en",{timeZone:el.dataset.offsetZone,timeZoneName:"longOffset"}).formatToParts(date).find(p => p.type === "timeZoneName");
        el.textContent=part.value === "GMT" ? "UTC +00:00" : part.value.replace("GMT","UTC ");
    });
    TIMEZONES.forEach(
        item => {

            const timeFormatter =
                new Intl.DateTimeFormat(
                    "en-GB",
                    {
                        timeZone:
                            item.zone,
                        hour:
                            "2-digit",
                        minute:
                            "2-digit",
                        second:
                            "2-digit",
                        hour12:
                            false,
                    }
                );

            const dateFormatter =
                new Intl.DateTimeFormat(
                    "en-GB",
                    {
                        timeZone:
                            item.zone,
                        day:
                            "2-digit",
                        month:
                            "2-digit",
                        year:
                            "numeric",
                    }
                );

            document.querySelector(
                `[data-zone="${item.zone}"]`
            ).textContent =
                timeFormatter.format(
                    date
                );

            document.querySelector(
                `[data-date-zone="${item.zone}"]`
            ).textContent =
                dateFormatter.format(
                    date
                );
        }
    );
}


function configureExpandAll() {
    document.querySelectorAll("main details").forEach(panel=>panel.addEventListener("toggle",updateExpandToggle));
    document.getElementById("expand-toggle").addEventListener("change",event=>{
        const expand=event.target.checked;
        document.querySelectorAll("main details").forEach(panel=>{panel.open=expand;});
        document.querySelectorAll(".client-card").forEach(card=>{
            card.classList.toggle("open",expand);
            if(expand) openCards.add(card.dataset.address); else openCards.delete(card.dataset.address);
            card.querySelector(".caret").textContent=expand ? "▲" : "▼";
        });
        saveOpenCards(); updateExpandToggle();
    });
}

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        if(!await authenticateDashboard())return;
        await loadSharedSettings();
        setInterval(loadSharedSettings,30000);
        configureTheme();
        configureSettings();
        configureGraphs();
        configureAcquisition();
        configureClocks();
        setInterval(configureTheme, 60000);
        configureExpandAll();

        buildClocks();

        document.getElementById(
            "search"
        ).addEventListener(
            "input",
            renderClients
        );

        document.getElementById(
            "sort-select"
        ).addEventListener(
            "change",
            renderClients
        );

        try {
            if(can("time.view") || can("clocks.view") || can("clocks.amend"))await synchroniseNtpClock();
        }
        catch (error) {
            showError(
                error.message
            );
        }

        await refreshServer();

        updateClocks();

        setInterval(
            updateClocks,
            1000
        );

        setInterval(
            refreshServer,
            REFRESH_INTERVAL
        );

        setInterval(
            async () => {
                try {
                    if(can("time.view") || can("clocks.view") || can("clocks.amend"))await synchroniseNtpClock();
                }
                catch (error) {
                    showError(
                        error.message
                    );
                }
            },
            NTP_SYNC_INTERVAL
        );
    }
);
