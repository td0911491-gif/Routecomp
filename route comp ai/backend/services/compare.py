"""
compare.py
Pure logic, no network calls. Takes a road distance (km, from OSRM) and a
great-circle distance (km, for flight legs) and returns every transport mode
that makes sense for that trip, each with estimated time, cost, and comfort.

All prices are rough, transparent estimates (openly documented below) since
free real-time fare APIs for flights/trains/buses do not exist. This is
labelled clearly in the UI as "estimated", not "live pricing".
"""

from dataclasses import dataclass, asdict


@dataclass
class ModeResult:
    mode: str            # e.g. "Walking", "Train (Economy)"
    tier: str            # "standard" | "premium"
    distance_km: float
    duration_hours: float
    cost_usd: float
    comfort: int         # 1 (rough) to 5 (luxury)
    notes: str
    cost_inr: float = 0.0

    def __post_init__(self):
        if not self.cost_inr:
            self.cost_inr = round(self.cost_usd * USD_TO_INR, 2)


# ---- Tunable constants, kept in one place so they're easy to justify/adjust ----

WALK_SPEED_KMH = 5
BIKE_SPEED_KMH = 15
BUS_SPEED_KMH = 55          # includes stops
TRAIN_SPEED_KMH = 90        # regional/intercity average
CAR_SPEED_KMH = 70          # includes traffic/lights
FLIGHT_SPEED_KMH = 780
FLIGHT_OVERHEAD_HOURS = 2.5  # security, boarding, taxi, baggage

BUS_COST_PER_KM = 0.07
TRAIN_COST_PER_KM = 0.12
TRAIN_PREMIUM_MULT = 2.3        # first class
CAR_COST_PER_KM = 0.55          # rideshare/taxi all-in
CAR_BASE_FARE = 3.0
BIKE_RENTAL_PER_KM = 0.10
FLIGHT_COST_PER_KM = 0.13
FLIGHT_BASE_FARE = 45.0
FLIGHT_PREMIUM_MULT = 3.2        # business class

USD_TO_INR = 95.2  # approximate mid-market rate, Aug 2026 — not live; update as needed

# Distance windows where a mode is realistic to offer at all
WALK_MAX_KM = 8
BIKE_MAX_KM = 40
BUS_MAX_KM = 1200
TRAIN_MAX_KM = 1500
CAR_MAX_KM = 1200
FLIGHT_MIN_KM = 180


def _round(x, n=2):
    return round(x, n)


def get_transport_options(road_km: float, air_km: float) -> list[ModeResult]:
    """
    road_km: driving-network distance (walking/cycling/bus/train/car approximate off this)
    air_km:  great-circle distance (flight distance)
    """
    options: list[ModeResult] = []

    if road_km <= WALK_MAX_KM:
        options.append(ModeResult(
            mode="Walking", tier="standard",
            distance_km=_round(road_km),
            duration_hours=_round(road_km / WALK_SPEED_KMH),
            cost_usd=0.0, comfort=1,
            notes="Free, zero emissions, only realistic for short hops."
        ))

    if road_km <= BIKE_MAX_KM:
        options.append(ModeResult(
            mode="Cycling", tier="standard",
            distance_km=_round(road_km),
            duration_hours=_round(road_km / BIKE_SPEED_KMH),
            cost_usd=_round(road_km * BIKE_RENTAL_PER_KM),
            comfort=2,
            notes="Assumes a rented city bike; free if you own one."
        ))

    if road_km <= BUS_MAX_KM:
        options.append(ModeResult(
            mode="Bus", tier="standard",
            distance_km=_round(road_km),
            duration_hours=_round(road_km / BUS_SPEED_KMH),
            cost_usd=_round(max(2.0, road_km * BUS_COST_PER_KM)),
            comfort=2,
            notes="Cheapest motorized option on most routes."
        ))

    if road_km <= TRAIN_MAX_KM:
        base_cost = max(4.0, road_km * TRAIN_COST_PER_KM)
        options.append(ModeResult(
            mode="Train (Economy)", tier="standard",
            distance_km=_round(road_km),
            duration_hours=_round(road_km / TRAIN_SPEED_KMH),
            cost_usd=_round(base_cost),
            comfort=3,
            notes="Good balance of speed, cost, and comfort."
        ))
        options.append(ModeResult(
            mode="Train (First Class)", tier="premium",
            distance_km=_round(road_km),
            duration_hours=_round(road_km / TRAIN_SPEED_KMH),
            cost_usd=_round(base_cost * TRAIN_PREMIUM_MULT),
            comfort=4,
            notes="Wider seats, quieter cabin, same speed as economy."
        ))

    if road_km <= CAR_MAX_KM:
        options.append(ModeResult(
            mode="Car / Rideshare", tier="standard",
            distance_km=_round(road_km),
            duration_hours=_round(road_km / CAR_SPEED_KMH),
            cost_usd=_round(CAR_BASE_FARE + road_km * CAR_COST_PER_KM),
            comfort=3,
            notes="Door to door, but fares scale fastest with distance."
        ))

    if air_km >= FLIGHT_MIN_KM:
        base_cost = FLIGHT_BASE_FARE + air_km * FLIGHT_COST_PER_KM
        flight_hours = FLIGHT_OVERHEAD_HOURS + air_km / FLIGHT_SPEED_KMH
        options.append(ModeResult(
            mode="Flight (Economy)", tier="standard",
            distance_km=_round(air_km),
            duration_hours=_round(flight_hours),
            cost_usd=_round(base_cost),
            comfort=4,
            notes="Fastest option once distance clears ~180 km."
        ))
        options.append(ModeResult(
            mode="Flight (Business)", tier="premium",
            distance_km=_round(air_km),
            duration_hours=_round(flight_hours - 0.2),  # lounge/priority boarding saves a little
            cost_usd=_round(base_cost * FLIGHT_PREMIUM_MULT),
            comfort=5,
            notes="Priority everything, lie-flat seats on longer routes."
        ))

    return options


def rank_options(options: list[ModeResult]) -> dict:
    if not options:
        return {"cheapest": None, "fastest": None, "most_luxurious": None}

    cheapest = min(options, key=lambda o: o.cost_usd)
    fastest = min(options, key=lambda o: o.duration_hours)
    # luxury: highest comfort first, cheaper of the ties second
    most_luxurious = max(options, key=lambda o: (o.comfort, -o.cost_usd))

    return {
        "cheapest": cheapest.mode,
        "fastest": fastest.mode,
        "most_luxurious": most_luxurious.mode,
    }


def compare(road_km: float, air_km: float) -> dict:
    options = get_transport_options(road_km, air_km)
    badges = rank_options(options)
    return {
        "options": [asdict(o) for o in options],
        "badges": badges,
    }
