# Elevator Simulation: Effect of Advance Destination Notice on Wait Times

A discrete-event, time-stepped simulation model comparing a **Traditional Elevator Dispatch Algorithm** against a **Modern Advance Destination Notice Algorithm** (Destination Dispatch) in a 34-floor residential high-rise building.

---

## 🔬 Scientific Premise

Traditional elevator systems require a passenger to press an UP or DOWN button in the hallway, wait for an elevator, and select their destination floor only after boarding. In contrast, modern destination dispatch systems require passengers to enter their destination floor at a hallway kiosk in advance.

This project simulates 365 days (trials) of elevator operations for both systems to determine whether advance destination notice produces a statistically significant improvement by measuring:
1. **90th Percentile Daily Wait Time** (seconds between call placement and boarding).
2. **Slowest Elevator Speed** (floors traveled / total occupied time) across the 8 elevators.
3. **90% Confidence Intervals** for both metrics over 365 trials.

**Hypothesis Criterion**: If there is significant overlap between the 90% confidence intervals of the two systems, there is either no or only marginal benefit to implementing the modern algorithm.

---

## 🏢 Simulation Specification

- **Building Layout (34 Floors)**:
  - **Floor 1**: Lobby
  - **Floors 2–9**: Parking garages
  - **Floor 10**: Study floor
  - **Floors 11–33**: Residential (23 floors, 10 4-person apartments = 40 residents/floor, **920 total residents**)
  - **Floor 34**: Sky Lounge
- **Assigned Parking**:
  $$\text{Parking Floor} = floor((Apartment floor - 4)/3)$$
- **Elevators**:
  - **Count**: 8 elevators, all spanning Floor 1 to Floor 34
  - **Capacity**: 10 passengers max
  - **Speed**: 1 floor per second
  - **Boarding / Exiting Delay**: 3 seconds per passenger
- **Time Step**: $1\text{ second}$ discrete tick
- **Daily Routine (1,840 calls/day)**:
  - **Wake-up (Morning Outbound)**: $\mathcal{N}(\mu=9\text{am}, \sigma=1.5\text{h})$ bounded to [6am, 12pm].
    - Activity choices:
      - 70% Leave building (50% Lobby [Floor 1], 50% Assigned Parking Floor [Floors 2–9])
      - 20% Study floor [Floor 10]
      - 10% Sky lounge [Floor 34]
  - **Bedtime (Night Inbound)**: $\mathcal{N}(\mu=12\text{am}, \sigma=1.5\text{h})$ bounded to [9pm, 3am]. Returns from activity floor to apartment floor.
- **Trial Duration**: 24 hours ($86,400\text{ seconds}$) per trial; **365 trials**.

---

## 📐 Algorithm Details

### 1. Traditional Algorithm
- A passenger presses **UP** or **DOWN** at their floor.
- The system chooses the **closest elevator traveling in the desired direction** that has not yet passed the caller's floor.
- If none qualify, the **closest idle elevator** is dispatched (breaking ties uniformly at random).
- Up to 10 requests along the same corridor are batched into a single elevator, leaving other elevators available to service independent requests.
- Once the passenger boards, they register their destination inside the elevator, which adds it to the elevator's destination queue.

### 2. Modern Algorithm (Advance Destination Notice)
- A passenger inputs their **destination floor** directly at the hallway kiosk.
- The system chooses the **closest elevator traveling towards the destination floor on a path that will pass by the passenger's current floor** before reaching the destination floor.
- If none qualify, the **closest idle elevator** is dispatched (breaking ties uniformly at random).
- Crucially, the elevator immediately receives **both the pickup floor and the destination floor** in its destination queue, optimizing routing and grouping compatible trips.

In both algorithms, each elevator prioritizes stops closest to its current floor in its direction of travel (LOOK/SCAN algorithm) and sits idle when empty with no active requests.

---

## 📊 Experimental Results & Analysis (365-Day Study)

The full 365-day experiment ($N = 365$ independent 24-hour trials, 671,600 total elevator calls) was executed and recorded in [`results.json`](results.json).

### 1. 90th Percentile Waiting Time

| Metric | Traditional Algorithm | Modern Algorithm | Difference |
| :--- | :---: | :---: | :---: |
| **Sample Size ($N$)** | 365 trials | 365 trials | — |
| **Mean 90th %ile Wait** | **29.78 s** | **28.89 s** | **-0.90 s (-3.0%)** |
| **Standard Deviation ($\sigma$)** | 0.4730 s | 0.3933 s | -16.8% variance |
| **Standard Error ($\text{SE}$)** | 0.0248 s | 0.0206 s | — |
| **Margin of Error ($90\%$ CI)** | $\pm 0.0408\text{ s}$ | $\pm 0.0340\text{ s}$ | — |
| **$90\%$ Confidence Interval** | **[29.7419 s, 29.8236 s]** | **[28.8537 s, 28.9216 s]** | **NO OVERLAP** |

- **Confidence Interval Overlap**: **None** (Separation of **$0.8203\text{ seconds}$**).
- **Statistical Significance**: The upper bound of the Modern algorithm ($28.9216\text{ s}$) is strictly lower than the lower bound of the Traditional algorithm ($29.7419\text{ s}$), demonstrating a statistically significant reduction in waiting times.

---

### 2. Slowest Elevator Speed

| Metric | Traditional Algorithm | Modern Algorithm | Difference |
| :--- | :---: | :---: | :---: |
| **Sample Size ($N$)** | 365 trials | 365 trials | — |
| **Mean Slowest Speed** | **0.7191 floors/s** | **0.7585 floors/s** | **+0.0393 floors/s (+5.5%)** |
| **Standard Deviation ($\sigma$)** | 0.0084 floors/s | 0.0078 floors/s | -6.5% variance |
| **Standard Error ($\text{SE}$)** | 0.00044 floors/s | 0.00041 floors/s | — |
| **Margin of Error ($90\%$ CI)** | $\pm 0.00072\text{ floors/s}$ | $\pm 0.00068\text{ floors/s}$ | — |
| **$90\%$ Confidence Interval** | **[0.7184 floors/s, 0.7198 floors/s]** | **[0.7578 floors/s, 0.7591 floors/s]** | **NO OVERLAP** |

- **Confidence Interval Overlap**: **None** (Separation of **$0.0379\text{ floors/s}$**).
- **Statistical Significance**: The slowest elevator in the Modern algorithm operates at a statistically significantly higher speed because advance destination notice groups passengers heading to the same floors, reducing intermediate stopping and door delays.

---

### 3. Night Return Completion Rate (Residents Back Before 6:00 AM)

| Metric | Traditional Algorithm | Modern Algorithm | Comparison |
| :--- | :---: | :---: | :---: |
| **Sample Size ($N$)** | 365 trials | 365 trials | — |
| **Mean Return Rate (%)** | **100.00%** | **100.00%** | **Identical** |
| **Mean Residents Returned** | **920.00 / 920** | **920.00 / 920** | **Identical** |
| **Standard Deviation ($\sigma$)** | 0.0000% | 0.0000% | Zero variance |
| **Standard Error ($\text{SE}$)** | 0.0000% | 0.0000% | — |
| **Margin of Error ($90\%$ CI)** | $\pm 0.0000\%$ | $\pm 0.0000\%$ | — |
| **$90\%$ Confidence Interval** | **[100.0000%, 100.0000%]** | **[100.0000%, 100.0000%]** | **Full Overlap** |

- **Operational Setup**:
  - Resident bedtime return calls are initiated between 9:00 PM and 3:00 AM ($t = 54,000\text{s}$ to $75,600\text{s}$), with late-night callers placing their requests at the 3:00 AM cutoff.
  - The elevator fleet operates continuously through 6:00 AM ($t = 86,400\text{s}$), providing a generous 3-hour operational window to drain all traffic.
  - With **capacity overflow re-queuing** active in the Traditional Algorithm, any passengers who cannot board a full elevator (10/10 capacity) have their hall call automatically re-dispatched to the next available car, ensuring **100.00% of residents (920 / 920)** across all 365 trials safely return to bed before 6:00 AM.

---

### 4. Fleet Traffic Distribution (Workload Balance)

Average passenger pickups per elevator across all 365 trials:

| Elevator | Traditional Mean Pickups | Modern Mean Pickups | Share of Fleet Workload |
| :---: | :---: | :---: | :---: |
| **Elev 0** | 231.1 | 230.5 | 12.5% |
| **Elev 1** | 228.7 | 230.3 | 12.5% |
| **Elev 2** | 228.6 | 231.3 | 12.6% |
| **Elev 3** | 229.4 | 229.0 | 12.5% |
| **Elev 4** | 228.1 | 230.0 | 12.5% |
| **Elev 5** | 234.3 | 230.6 | 12.5% |
| **Elev 6** | 232.5 | 230.9 | 12.5% |
| **Elev 7** | 227.3 | 227.4 | 12.4% |
| **Total** | **1,840.0** | **1,840.0** | **100.0%** |

---

### 5. Statistical Significance vs. Pragmatic Real-World Impact

While the mathematical simulation definitively demonstrates statistical significance under formal hypothesis testing criteria, a practical engineering assessment reveals that the real-world impact on resident experience is negligible:

1. **Waiting Time Difference (< 1 Second)**:
   - *Statistical Reality*: The 90% confidence intervals show zero overlap (separated by $0.8203\text{s}$, $p < 0.05$), formally validating that Modern Destination Dispatch outperforms Traditional Dispatch.
   - *Pragmatic Reality*: The actual absolute difference in the 90th percentile wait time is **only 0.89 seconds** (**28.89s vs. 29.78s**). To a human standing in an elevator lobby, a fraction of a second is completely imperceptible and has zero practical bearing on comfort, punctuality, or resident satisfaction.
2. **Speed Difference (< 0.05 Floors/Second)**:
   - *Statistical Reality*: The slowest elevator speed shows zero CI overlap (separated by $0.0379\text{ floors/s}$, $p < 0.05$).
   - *Pragmatic Reality*: The difference is **only 0.039 floors/second** (**0.7585 vs. 0.7191 floors/s**). For a typical 10-floor journey, this amounts to a transit time difference of less than 0.7 seconds. Human vestibular and visual senses cannot perceive a velocity change of 0.04 floors/s in a smooth vertical cab.
3. **Capital Expenditure & Complexity**:
   - Modern Destination Dispatch requires dedicated touch kiosks on all 34 floors, expensive proprietary group controllers, and tenant habit re-education (passengers cannot change their mind or select floors inside the car).
   - In massive commercial office towers with thousands of workers arriving during a compressed 15-minute morning peak, destination dispatch provides substantial crowd control. However, in a **residential apartment tower** where resident routines naturally disperse across several morning and evening hours, the massive financial and operational costs yield virtually zero tangible benefit to residents.

---

### 6. Final Scientific Conclusion

> **Conclusion**: 
> 1. **Academic / Statistical Criterion**: The simulation satisfies the rigorous hypothesis testing criteria: the 90% confidence intervals for both 90th percentile wait times and slowest car speeds show **zero overlap**, proving that the Modern Advance Destination Notice system provides a statistically significant operational advantage over the Traditional algorithm.
> 2. **Pragmatic / Engineering Criterion**: Because the wait time advantage is **< 1.0 second** and the speed advantage is **< 0.05 floors/second**, the performance gains are **imperceptible to residents**, meaning the substantial capital expenditure of retrofitting an existing residential building to destination dispatch is not practically justified.

---

## 📁 Codebase Architecture

```
Elevator_Sims/
├── config.py             # Simulation constants, building layout, parking formula, distributions
├── models.py             # Direction, PersonState enums, Person, CallRequest dataclasses
├── elevator.py          # Elevator class: LOOK/SCAN movement, door delays, capacity, travel metrics
├── traditional.py        # Traditional dispatch algorithm implementation with traffic balancing
├── modern.py             # Modern destination dispatch algorithm implementation with traffic balancing
├── simulation.py         # Daily trial engine (resident generation, 24h event loop, metrics collection)
├── stats.py              # 90% Confidence interval calculations and overlap evaluation
├── runner.py             # Parallel multi-trial orchestrator (CLI, multiprocessing, reporting)
├── results.json          # 365-trial empirical dataset and aggregate statistical analysis
├── tests/                # Automated test suite (17 unit tests)
│   ├── test_building.py  # Building parameters, parking formula, resident schedules
│   ├── test_elevator.py  # Elevator movement, door timing, capacity, speed metrics
│   ├── test_dispatchers.py# Traditional and modern dispatch decision verification
│   ├── test_balancing.py # Randomized idle selection and same-path batching tests
│   ├── test_stats.py     # Confidence interval calculations and overlap detection
│   └── test_simulation_smoke.py # Integration smoke test
└── README.md             # Documentation, results, and usage guide
```

---

## 🚀 How to Run

### 1. Run Automated Test Suite
```bash
python3 -m unittest discover -s tests
```

### 2. Run a Quick Test (1 or 5 trials)
```bash
# Run 1 trial for both algorithms
python3 runner.py --trials 1

# Run 5 trials using 4 CPU workers
python3 runner.py --trials 5 --workers 4
```

### 3. Run the Full 365-Trial Experiment
```bash
# Full 365 trials with parallel workers and JSON output
python3 runner.py --trials 365 --workers 8 --output results.json
```

### 4. CLI Arguments
- `--trials N`: Number of trials to run (default: 365).
- `--algorithm [both|traditional|modern]`: Which algorithm to run (default: `both`).
- `--workers W`: Number of CPU workers for parallel execution (default: all available cores).
- `--seed S`: Base random seed for reproducible comparisons (default: 42).
- `--output PATH`: Path to export summary statistics as JSON.
