"""Small independent-unit statistics. This module is copied into execution packages."""

import csv
import itertools
import io
import math
import random

MAX_ROWS = 2000


def read_numeric_csv(path):
    with path.open("rb") as stream:
        raw = stream.read(2 * 1024 * 1024 + 1)
    return read_numeric_bytes(raw)


def read_numeric_bytes(raw):
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("numeric input exceeds its size limit")
    units, values, labels = set(), [], []
    with io.StringIO(raw.decode("utf-8"), newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["unit", "label", "value"]:
            raise ValueError("CSV columns must be unit,label,value")
        for row in reader:
            if len(values) >= MAX_ROWS or None in row or any(value is None for value in row.values()):
                raise ValueError("numeric input is malformed or exceeds its row limit")
            if not row["unit"] or row["unit"] in units or row["label"] not in ("0", "1"):
                raise ValueError("units must be unique and group labels must be zero or one")
            value = float(row["value"])
            if not math.isfinite(value):
                raise ValueError("numeric values must be finite")
            units.add(row["unit"])
            labels.append(int(row["label"]))
            values.append(value)
    if min(labels.count(0), labels.count(1)) < 2:
        raise ValueError("each independent group requires at least two units")
    return values, labels


def mean_difference(values, labels):
    left = [value for value, label in zip(values, labels) if label == 0]
    right = [value for value, label in zip(values, labels) if label == 1]
    if not left or not right or len(values) != len(labels):
        raise ValueError("two nonempty groups of matching length are required")
    return math.fsum(right) / len(right) - math.fsum(left) / len(left)


def quantile(values, fraction):
    if not values or not 0 <= fraction <= 1:
        raise ValueError("invalid quantile request")
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def permutation_test(values, labels, seed=0, draws=999, exact_limit=5000):
    if not 1 <= draws <= 10000 or not 1 <= exact_limit <= 5000:
        raise ValueError("permutation budget is invalid")
    observed = mean_difference(values, labels)
    count_one = labels.count(1)
    combinations = math.comb(len(values), count_one)
    generator = random.Random(seed)
    assignments = itertools.combinations(range(len(values)), count_one) if combinations <= exact_limit else (
        generator.sample(range(len(values)), count_one) for _ in range(draws))
    null = []
    for indices in assignments:
        selected = set(indices)
        null.append(mean_difference(values, [int(index in selected) for index in range(len(values))]))
    extreme = sum(abs(value) >= abs(observed) or math.isclose(
        abs(value), abs(observed), rel_tol=1e-12, abs_tol=0.0) for value in null)
    exact = combinations <= exact_limit
    probability = extreme / len(null) if exact else (extreme + 1) / (len(null) + 1)
    average = math.fsum(null) / len(null)
    variance = math.fsum((value - average) ** 2 for value in null) / len(null)
    return {"effect": observed, "p_value": probability, "draws": len(null), "exact": exact,
            "null_mean": average, "null_sd": math.sqrt(variance)}


def bootstrap_difference(values, labels, seed=0, draws=999, coverage=0.95):
    if not 100 <= draws <= 10000 or not 0 < coverage < 1:
        raise ValueError("bootstrap budget or coverage is invalid")
    left = [value for value, label in zip(values, labels) if label == 0]
    right = [value for value, label in zip(values, labels) if label == 1]
    if min(len(left), len(right)) < 2:
        raise ValueError("bootstrap requires two independent groups")
    generator = random.Random(seed)
    distribution = []
    for _ in range(draws):
        left_mean = math.fsum(generator.choices(left, k=len(left))) / len(left)
        right_mean = math.fsum(generator.choices(right, k=len(right))) / len(right)
        distribution.append(right_mean - left_mean)
    tail = (1 - coverage) / 2
    return {"effect": mean_difference(values, labels), "lower": quantile(distribution, tail),
            "upper": quantile(distribution, 1 - tail), "coverage": coverage}
