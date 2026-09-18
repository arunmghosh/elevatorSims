"""Main trial orchestration script with parallel processing and statistical reporting."""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import numpy as np
from typing import List, Dict, Any, Tuple

from config import DEFAULT_NUM_TRIALS
from simulation import run_single_trial, TrialResult
from stats import (
    compute_confidence_interval,
    evaluate_confidence_interval_overlap,
    ConfidenceInterval,
)


def _worker_trial(args: Tuple[str, int]) -> TrialResult:
    """Helper worker function for multiprocessing."""
    algo, seed = args
    return run_single_trial(algo, seed)


from typing import Tuple


def run_experiment(
    algorithm: str,
    num_trials: int = DEFAULT_NUM_TRIALS,
    workers: int = 4,
    base_seed: int = 42,
) -> List[TrialResult]:
    """Runs N trials in parallel for a given algorithm."""
    tasks = [(algorithm, base_seed + i) for i in range(num_trials)]
    results: List[TrialResult] = []

    start_time = time.time()
    print(f"Starting {num_trials} trials for algorithm: '{algorithm}' using {workers} workers...")

    if workers <= 1:
        for idx, task in enumerate(tasks):
            res = _worker_trial(task)
            results.append(res)
            if (idx + 1) % max(1, num_trials // 10) == 0:
                elapsed = time.time() - start_time
                print(f"  Completed {idx + 1}/{num_trials} trials ({elapsed:.1f}s elapsed)")
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {executor.submit(_worker_trial, task): i for i, task in enumerate(tasks)}
            completed = 0
            for future in as_completed(future_to_idx):
                res = future.result()
                results.append(res)
                completed += 1
                if completed % max(1, num_trials // 10) == 0:
                    elapsed = time.time() - start_time
                    print(f"  Completed {completed}/{num_trials} trials ({elapsed:.1f}s elapsed)")

    elapsed = time.time() - start_time
    print(f"Finished {num_trials} trials for '{algorithm}' in {elapsed:.2f}s.\n")
    return results


def analyze_and_print_results(
    traditional_results: List[TrialResult],
    modern_results: List[TrialResult],
) -> Dict[str, Any]:
    """Calculates aggregate confidence intervals and checks for overlap."""
    print("=" * 80)
    print("                      AGGREGATE SIMULATION RESULTS")
    print("=" * 80)

    # 1. 90th percentile wait time
    trad_wait_p90 = [r.percentile_90_wait_time for r in traditional_results]
    mod_wait_p90 = [r.percentile_90_wait_time for r in modern_results]

    ci_trad_wait = compute_confidence_interval(trad_wait_p90, "Traditional 90th Percentile Wait Time (s)")
    ci_mod_wait = compute_confidence_interval(mod_wait_p90, "Modern 90th Percentile Wait Time (s)")

    print("\n--- 90th Percentile Waiting Time (90% Confidence Interval) ---")
    print(f"  Traditional Algorithm : {ci_trad_wait}")
    print(f"  Modern Algorithm      : {ci_mod_wait}")

    overlap_wait, amount_wait, conclusion_wait = evaluate_confidence_interval_overlap(ci_trad_wait, ci_mod_wait)
    print(f"\n  Wait Time Overlap Check:")
    print(f"  {conclusion_wait}")

    # 2. Slowest elevator speed
    trad_slow_speeds = [r.slowest_elevator_speed for r in traditional_results]
    mod_slow_speeds = [r.slowest_elevator_speed for r in modern_results]

    ci_trad_speed = compute_confidence_interval(trad_slow_speeds, "Traditional Slowest Elevator Speed (floors/s)")
    ci_mod_speed = compute_confidence_interval(mod_slow_speeds, "Modern Slowest Elevator Speed (floors/s)")

    print("\n--- Mean Slowest Elevator Speed (90% Confidence Interval) ---")
    print(f"  Traditional Algorithm : {ci_trad_speed}")
    print(f"  Modern Algorithm      : {ci_mod_speed}")

    overlap_speed, amount_speed, conclusion_speed = evaluate_confidence_interval_overlap(ci_trad_speed, ci_mod_speed)
    print(f"\n  Slowest Speed Overlap Check:")
    print(f"  {conclusion_speed}")

    # 3. Night return completion rate (residents back in apartment before 6:00 AM)
    trad_return_pcts = [r.residents_returned_percentage for r in traditional_results]
    mod_return_pcts = [r.residents_returned_percentage for r in modern_results]

    ci_trad_return = compute_confidence_interval(trad_return_pcts, "Traditional Night Return Rate (%)")
    ci_mod_return = compute_confidence_interval(mod_return_pcts, "Modern Night Return Rate (%)")

    print("\n--- Night Return Rate: Residents Back in Apartment Before 6:00 AM (90% CI) ---")
    print(f"  Traditional Algorithm : {ci_trad_return}")
    print(f"  Modern Algorithm      : {ci_mod_return}")

    # 4. Elevator traffic distribution across the 8 elevators
    print("\n--- Mean Passenger Pickups per Elevator (Fleet Traffic Balance) ---")
    header = "Elevator | Traditional Mean Pickups | Modern Mean Pickups"
    print(f"  {header}")
    print("  " + "-" * len(header))
    trad_fleet_pickups = np.mean([r.elevator_pickups for r in traditional_results], axis=0)
    mod_fleet_pickups = np.mean([r.elevator_pickups for r in modern_results], axis=0)
    for eid in range(len(trad_fleet_pickups)):
        print(f"   Elev {eid} | {trad_fleet_pickups[eid]:24.1f} | {mod_fleet_pickups[eid]:19.1f}")

    print("=" * 80)

    return {
        "wait_time": {
            "traditional": asdict(ci_trad_wait),
            "modern": asdict(ci_mod_wait),
            "overlap": overlap_wait,
            "overlap_amount": amount_wait,
            "conclusion": conclusion_wait,
        },
        "slowest_speed": {
            "traditional": asdict(ci_trad_speed),
            "modern": asdict(ci_mod_speed),
            "overlap": overlap_speed,
            "overlap_amount": amount_speed,
            "conclusion": conclusion_speed,
        },
        "night_return_rate": {
            "traditional": asdict(ci_trad_return),
            "modern": asdict(ci_mod_return),
            "traditional_mean_count": float(np.mean([r.residents_returned_count for r in traditional_results])),
            "modern_mean_count": float(np.mean([r.residents_returned_count for r in modern_results])),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Elevator Simulation: Traditional vs Advance Destination Notice")
    parser.add_argument("--trials", type=int, default=DEFAULT_NUM_TRIALS, help=f"Number of trials (default: {DEFAULT_NUM_TRIALS})")
    parser.add_argument("--algorithm", type=str, choices=["both", "traditional", "modern"], default="both", help="Algorithm to run")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 4, help="Worker processes for multiprocessing")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed")
    parser.add_argument("--output", type=str, default=None, help="Optional JSON file to save aggregate statistics")

    args = parser.parse_args()

    if args.algorithm == "both":
        trad_results = run_experiment("traditional", args.trials, args.workers, args.seed)
        mod_results = run_experiment("modern", args.trials, args.workers, args.seed)
        summary = analyze_and_print_results(trad_results, mod_results)
        if args.output:
            with open(args.output, "w") as f:
                json.dump(summary, f, indent=2)
            print(f"Saved results to {args.output}")

    elif args.algorithm == "traditional":
        trad_results = run_experiment("traditional", args.trials, args.workers, args.seed)
        wait_p90 = [r.percentile_90_wait_time for r in trad_results]
        slow_speeds = [r.slowest_elevator_speed for r in trad_results]
        print(compute_confidence_interval(wait_p90, "Traditional 90th Percentile Wait Time (s)"))
        print(compute_confidence_interval(slow_speeds, "Traditional Slowest Elevator Speed (floors/s)"))

    elif args.algorithm == "modern":
        mod_results = run_experiment("modern", args.trials, args.workers, args.seed)
        wait_p90 = [r.percentile_90_wait_time for r in mod_results]
        slow_speeds = [r.slowest_elevator_speed for r in mod_results]
        print(compute_confidence_interval(wait_p90, "Modern 90th Percentile Wait Time (s)"))
        print(compute_confidence_interval(slow_speeds, "Modern Slowest Elevator Speed (floors/s)"))


if __name__ == "__main__":
    main()
