"""Topic labels for contract names and Kalshi series.

A rule list, first match wins, applied to the text the CFTC or the platform
published (a filing's product name, a series ticker plus an event title).
It is a reading aid, not a ledger field: the raw text is always kept next to
the label so any row can be checked by hand. Change the rules by pull
request with the examples that motivated the change.

Order matters: specific sports before generic words ("points", "record"),
and player props before the league so "NBA player points" is a prop.
"""

from __future__ import annotations

import re

SPORTS = {
    "Props", "NFL", "College football", "NBA", "College basketball", "WNBA", "MLB", "NHL",
    "Soccer", "Golf", "Other basketball", "Tennis", "Table tennis", "Combat sports", "Motorsport", "Esports", "Cricket", "Other sports",
}

RULES: list[tuple[str, str]] = [
    # Props: player stat lines and prop series (player or game props; filings rarely say which).
    ("Props", r"<stat>|<statistic>|ENTITYSTAT|PLAYERSTAT|player stat|player prop|\bprop\b|prop series|\bstat series|\bstat anchor|football stat\b|basketball stat\b|baseball stat\b|hockey stat\b|"
                     r"first touchdown|anytime touchdown|FIRSTTD|passing yards|rushing yards|receiving yards|RECYDS|PASSYDS|RUSHYDS|strokes during|"
                     r"KX(?:NBA|NFL|NHL|MLB|WNBA|NCAAF|NCAAB)(?:PTS|AST|REB|3PT|TD|REC|RECYDS|PASSYDS|RUSHYDS|SOG|HR|HITS|KS|STL|BLK)\b"),
    ("Esports", r"esport|counter.?strike|\bCS2\b|league of legends|\bLOL\b|valorant|dota|call of duty|KXCS2|KXLOL|KXVAL|KXDOTA|KXCODGAME"),
    ("Table tennis", r"table tennis|\bWTT\b|TTCUP|TTELITE|WTTWIN"),
    ("Tennis", r"tennis|\bATP\b|\bWTA\b|\bITF\b|KXATP|KXWTA|KXITF|davis cup"),
    ("Golf", r"golf|\bPGA\b|\bLPGA\b|\bLIV\b|ryder cup|KXPGA|KXLPGA|masters tournament"),
    ("Combat sports", r"\bUFC\b|boxing|\bMMA\b|KXUFC|KXBOX|bout"),
    ("Motorsport", r"\bF1\b|formula 1|formula one|NASCAR|indycar|grand prix|KXF1|KXNASCAR"),
    ("Cricket", r"cricket|\bT20\b|\bIPL\b|test match|KXT20|KXIPL"),
    ("WNBA", r"WNBA"),
    ("Other basketball", r"euroleague|\bNBL\b|\bFIBA\b"),
    ("College basketball", r"NCAA.{0,30}basketball|NCAAM|NCAAW|NCAAB|college basketball|COLLEGEBASKETBALL|march madness|KXNCAAMB|KXNCAAWB|KXNCAAB"),
    ("College football", r"college football|COLLEGEFOOTBALL|NCAAF|heisman|\bCFP\b|KXNCAAF"),
    ("NFL", r"\bNFL|super bowl|pro football|PROFOOTBALL|^football\b|KXNFL|KXSB\b"),
    ("NBA", r"\bNBA|PROBASKETBALL|KXNBA"),
    ("MLB", r"\bMLB|PROBASEBALL|world series|baseball|\bNPB\b|\bKBO\b|KXMLB"),
    ("NHL", r"\bNHL|PROHOCKEY|stanley cup|hockey|KXNHL"),
    ("Soccer", r"soccer|premier league|\bEPL\b|champions league|\bUCL\b|\bMLS\b|la liga|serie a|bundesliga|ligue 1|FIFA|world cup|ballon d.or|"
               r"CONCACAF|\bUEL\b|\bUNL\b|\bEFL\b|\bSAFF\b|\bAFA\b|LALIGA|DIMAYOR|eredivisie|liga mx|saudi pro|goals during|KXUCL|KXEPL|KXMLS|KXLALIGA|KXSERIEA|KXBUND|KXLIGUE|KXBALLON|KXWC|PLGAME|LEAGUEGAME"),
    ("Other sports", r"olympic|rugby|darts|snooker|cycling|horse|derby|lacrosse|volleyball|handball|athletics|KXOLY"),
    ("Weather", r"ski season|mountain resort|temperature|rainfall|\brain\b|snow|hurricane|tornado|weather|climate|KXHIGH|KXLOW|KXRAIN|RAINCLI"),
    ("Crypto", r"bitcoin|\bBTC\b|ethereum|\bETH\b|solana|\bSOL\b|\bXRP\b|cardano|dogecoin|cryptocurrency|crypto|KXBTC|KXETH|KXSOL|KXXRP|KXDOGE"),
    ("Economics", r"\bCPI\b|inflation|federal reserve|\bfed\b|FOMC|interest rate|payroll|unemployment|jobless|\bGDP\b|recession|KXCPI|KXFED|KXGDP|KXPAYROLL"),
    ("Financials", r"S&P|nasdaq|\bdow\b|stock|equity index|treasury|yield|crude|\bWTI\b|\boil\b|gold|silver|natural gas|gas price|KXINX|KXNASDAQ|KXWTI|KXGOLD"),
    ("Elections and politics", r"election|president|senate|house of rep|governor|mayor|congress|primary|nominee|cabinet|approval rating|vote|party|"
                               r"supreme court|legislation|bill |KXPRES|KXSENATE|KXHOUSE|KXGOV|KXMAYOR|KXTRUMP"),
    ("Entertainment", r"oscar|academy award|grammy|emmy|golden globe|box office|billboard|album|movie|film|netflix|spotify|tv show|rotten tomatoes|KXOSCAR|KXGRAMMY|KXEMMY"),
    ("Companies and tech", r"apple|tesla|openai|nvidia|google|microsoft|amazon|meta|earnings|\bIPO\b|AI model|KXTSLA|KXAAPL|KXEARN"),
    ("Mentions", r"mention|say the word|KXMENTION|SAYS"),
    ("Education", r"admissions|applicant|university|college admission"),
]

_COMPILED = [(name, re.compile(rx, re.I)) for name, rx in RULES]


def topic(*texts: str | None) -> str:
    t = " | ".join(x for x in texts if x)
    for name, rx in _COMPILED:
        if rx.search(t):
            return name
    return "Other"


def is_sport(label: str) -> bool:
    return label in SPORTS
