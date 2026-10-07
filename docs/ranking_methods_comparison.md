# Hockey Ranking Methods: A Step-by-Step Comparison

This document provides a clear, step-by-step walkthrough of the two ranking algorithms currently under consideration for our hockey league: the **Colley Matrix** and the **Bradley-Terry / Elo Hybrid**. 

Because the math background of our committee is varied, this guide breaks down the core philosophies, the step-by-step implementations of the code, and what each method is fundamentally trying to achieve.

---

## Method 1: The Colley Matrix

### The Overall Goal: "Descriptive Fairness" (Resume-Based)
The primary goal of the Colley Matrix is to objectively evaluate a team's resume without bias. It does not try to predict future games or care about how badly a team won. It simply asks: *Who did you play, and did you win or lose?* 

By ignoring the margin of victory, it discourages teams from running up the score. It is mathematically designed to balance every team's record against the strength of their opponents.

### Step-by-Step Implementation

**Step 1: Start Everyone Equal**
At the beginning of the season, the algorithm assumes every team is perfectly average. Mathematically, it pretends every team starts with 1 win and 1 loss (a 0.500 record).

**Step 2: Build the Schedule Grid (The Matrix)**
The code builds a massive grid (or "matrix") that maps out every team's schedule.
- For each team, it counts their total number of games played.
- It also tracks exactly who they played and how many times they played each other.
- This creates an interconnected web linking every team in the league.

**Step 3: Record the Outcomes**
Instead of just counting whole wins and losses, the system assigns a value to each game to properly account for overtime:
- **Regulation Win:** $1.0$
- **Regulation Loss:** $0.0$
- **Overtime Tie:** $0.5$ to both teams
- **Overtime Win:** $0.667$ (A slight penalty compared to a regulation win)
- **Overtime Loss:** $0.333$ (A slight reward compared to a regulation loss)

These game values are added up to represent the team's total "performance score."

**Step 4: Balance the Web (Solve the Equations)**
This is where the heavy lifting happens. The algorithm takes the schedule grid (Step 2) and the game outcomes (Step 3) and solves a massive system of linear equations all at once. 

It continuously adjusts each team's rating up or down until the entire league is perfectly balanced. A team's final rating is a direct reflection of their win percentage mathematically adjusted for their Strength of Schedule (the average rating of their opponents).

---

## Method 2: The Bradley-Terry / Elo Hybrid

### The Overall Goal: "Predictive Accuracy" (Power-Based)
The primary goal of the Elo system is to measure a team's true "power" or strength. Unlike the Colley Matrix, which looks at the whole season at once, Elo is reactive and chronological. 

It treats every game as a data point to update its guess about how good a team is. It compares its *expected* outcome of a game against the *actual* outcome. This method can also factor in the Margin of Victory, rewarding teams that pull off blowouts (up to a capped limit).

### Step-by-Step Implementation

**Step 1: Set Initial Ratings**
Every team is assigned a starting base rating (e.g., 1500 points).

**Step 2: Calculate Expected Win Probability**
Before a game is even played, the algorithm compares Team A's current rating to Team B's current rating. Using the "Bradley-Terry" probability curve, it calculates exactly how likely each team is to win. 
- *Example:* If a 1600-rated team plays a 1200-rated team, the system expects the 1600-rated team to win easily (approx. 91% chance).

**Step 3: Play the Game & Find the Outcome**
Just like in the Colley method, the actual result of the game is converted into a score that respects overtime:
- Regulation Win = $1.0$, Regulation Loss = $0.0$
- Overtime Win = $0.667$, Overtime Loss = $0.333$
- Tie = $0.5$

**Step 4: Calculate the Margin of Victory Multiplier (Optional)**
If enabled, the code looks at the goal differential. However, to prevent teams from endlessly running up the score, it uses a "diminishing returns" formula. Winning by 4 goals gives a nice boost, but winning by 10 goals isn't treated as twice as impressive as winning by 5. The maximum goal differential can also be capped (e.g., at 4 goals).

**Step 5: The Rating Update (The Exchange)**
After the game, points are exchanged between the two teams.
- **If the expected outcome happens** (the favorite wins), the favorite gains a small number of points, and the underdog loses a small amount.
- **If an upset happens** (the underdog wins), the underdog steals a *massive* number of points from the favorite.
- The size of the exchange is determined by the difference between the *Actual Outcome* (Step 3) and the *Expected Outcome* (Step 2), multiplied by the Margin of Victory (Step 4) and a "Volatility Factor" (K-factor) which controls how fast ratings change.

---

## Summary Comparison for the Committee

| Feature | Colley Matrix | Bradley-Terry / Elo |
| :--- | :--- | :--- |
| **Primary Focus** | What you achieved (Resume) | How good you are right now (Power) |
| **Margin of Victory** | Completely ignored | Included (with diminishing returns) |
| **When Games Happen** | Doesn't matter (evaluates the whole season at once) | Matters greatly (chronological updates) |
| **Best Used For** | "Fair" playoff seeding based on pure wins/losses against schedule difficulty | Predicting future matchups, measuring current momentum, and separating talent gaps |
