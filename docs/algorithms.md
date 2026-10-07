**Prepared for**: MHC Rankings and Standings Committee

**Prepared by:** *Brad Campbell*

**Date**: Jun 17, 2026

---

# Ranking Algorithms Explanation

The rankings program supports two distinct mathematical approaches to ranking teams: the **Colley Matrix** and a hybrid **Bradley-Terry / Elo** system. Each model answers a fundamentally different question about team strength. 

This document explains the philosophy behind each method, the mathematical equations powering them, and the step-by-step process used to calculate the final rankings.

---

## 1. The Colley Matrix Method

### Overview
The Colley Matrix is a "resume-based" ranking system. Its primary goal is **descriptive fairness**. Instead of trying to predict who would win a theoretical game, it objectively evaluates what actually happened on the ice. 

It was originally designed for college football to provide a completely bias-free ranking. It does not care about the margin of victory (winning 1-0 is treated exactly the same as winning 10-0) to discourage teams from running up the score. It simply asks: *Who did you play, and did you win or lose?*

### How it Works
The Colley Matrix assumes every team starts with a completely average record (essentially 1 win and 1 loss, or a 0.500 win percentage). As games are played, the system solves a massive set of interconnected equations. It continuously balances a team's rating against the ratings of every team they played, adjusting everyone simultaneously until the entire league's interconnected web of wins and losses is perfectly balanced.

### The Math

The winning percentage for team $i$ is given by:

$$ wpct_{i} = \frac{n_{win,i}}{n_{tot,i}} $$

For the Colley method, we start with a slightly modified statistic.  The rating for team $i$ is given by:

$$ r_i = \frac{1 + n_{win,i}}{2 + n_{loss,i}} $$

From Colley's paper:
> All teams at the beginning of the season, when no games have been played, have an equal rating
> of 1/2. After winning one game, a team has a 2/3 rating, while a losing team has a 1/3 rating, i.e.,
> “twice as good,” much more sensible than 100% and 0%, or “infinitely better.”

The **effective** number of wins for a team can be rewritten as 

$$ n^{eff}_{win,i} = (n_{win,i} - n_{loss,i}) / 2 + n_{tot,i}/2 $$

The last bit can be written as 
$$ n_{tot,i}/2  = \sum^{n_{tot,i}}{1/2} $$

Given the average rating across the leagure is 1/2, this sum can be considered 
the sum of rankings of random teams with a rating of 1/2.  So we can rewrite the 
effective number of wins as:

$$ n^{eff}_{win,i} = (n_{win,i} - n_{loss,i}) / 2 + \sum^{n_{tot,i}}_{j=1}{r^i_j} $$

So the straight forward part is given by:

$$ b_i = 1 + \frac{n_{wins,i} - n_{losses,i}}{2} $$

The entire season is modeled as a system of linear equations represented by the formula:

$$ C \vec{r} = \vec{b} $$

Where:
- $C$ is the **Colley Matrix**, representing the schedule.
- $\vec{r}$ is the **ratings vector** (what we are trying to solve for).
- $\vec{b}$ is the **outcome vector**, representing team performance.

## How the Algorithm Works

**Step 1: Building the Matrix ($C$)**
For a league of $N$ teams, we create an $N \times N$ grid (matrix).

- **Diagonals ($C_{i,i}$):** For a specific team $i$, the value is exactly $2 + \text{Total Games Played}$. The "2" acts as a smoothing factor, ensuring no team mathematically breaks the system if they go undefeated or winless.
- **Off-Diagonals ($C_{i,j}$):** The relationship between Team $i$ and Team $j$. It is the *negative* number of times they played each other. If they played twice, the value is $-2$.

Here is the Colley matrix for the entire 2025-26 Season.

| Team   | BCC | Stars | NWQO | RM | RAM | Sherwood | SS | UML | Whit | WJ | Church | Woot |
|--------|:---:|:-----:|:----:|:--:|:---:|:--------:|:--:|:---:|:----:|:--:|:------:|:----:|
| BCC    | 14  | 0     | -1   | -1 | 0   | -2       | 0  | -1  | -2   | -1 | -2     | -2   |
| Stars  | 0   | 14    | -2   | -1 | -2  | -1       | -2 | -2  | -1   | -1 | 0      | 0    |
| NWQO   | -1  | -2    | 14   | -2 | -2  | 0        | -2 | -2  | 0    | -1 | 0      | 0    |
| RM     | -1  | -1    | -2   | 14 | -2  | 0        | -1 | -2  | -1   | 0  | -1     | -1   |
| RAM    | 0   | -2    | -2   | -2 | 14  | 0        | -2 | -2  | 0    | -1 | 0      | -1   |
| Sher   | -2  | -1    | 0    | 0  | 0   | 14       | -1 | 0   | -2   | -2 | -2     | -2   |
| SS     | 0   | -2    | -2   | -1 | -2  | -1       | 14 | -2  | -1   | 0  | -1     | 0    |
| UML    | -1  | -2    | -2   | -2 | -2  | 0        | -2 | 14  | 0    | -1 | 0      | 0    |
| Whit   | -2  | -1    | 0    | -1 | 0   | -2       | -1 | 0   | 14   | -1 | -2     | -2   |
| WJ     | -1  | -1    | -1   | 0  | -1  | -2       | 0  | -1  | -1   | 14 | -2     | -2   |
| Church | -2  | 0     | 0    | -1 | 0   | -2       | -1 | 0   | -2   | -2 | 14     | -2   |
| Woot   | -2  | 0     | 0    | -1 | -1  | -2       | 0  | 0   | -2   | -2 | -2     | 14   |



**Step 2: Building the Outcome Vector ($\vec{b}$)**
For each team $i$, their performance score traditionally calculates whole wins and losses as:
$$ b_i = 1 + \frac{\text{Wins}_i - \text{Losses}_i}{2} $$

**Overtime Adjustments:** To account for games that go to overtime, the share of a win is apportioned instead of using a binary win/loss. The game value ($v$) is assigned as follows:
- **Regulation Win:** $1.0$
- **Overtime Win:** $0.667$ 
- **Overtime Tie:** $0.5$ 
- **Overtime Loss:** $0.333$ 
- **Regulation Loss:** $0.0$

In this adjusted model, each game contributes $(v - 0.5)$ to a team's $b_i$ score. For example, an overtime win adds $0.167$ ($0.667 - 0.5$) to the vector instead of the standard $0.5$, reflecting a narrower margin of superiority.

**Step 3: Solving for Ratings ($\vec{r}$)**
Using standard linear algebra, the system finds the unique set of ratings ($\vec{r}$) that perfectly solves $C \vec{r} = \vec{b}$. 

**Step 4: Calculating Strength of Schedule (SOS)**
Once ratings are found, a team's SOS is simply the average rating of their opponents:
$$ \text{SOS}_i = \frac{C_{i,i} \times r_i - b_i}{\text{Total Games Played}} $$

### Inputs & Outputs
* **Inputs needed:** A list of teams and the results of all games (who played who, and who won). Scores are ignored.
* **Outputs produced:** A Colley Rating (usually hovering around 0.500 for an average team) and an SOS rating for each team.

---

## 2. The Bradley-Terry / Elo Hybrid Method

### Overview
The Bradley-Terry / Elo hybrid is a "power-based" ranking system. Its primary goal is **predictive accuracy**. It treats team strength as a hidden variable and uses every single game as a data point to update its guess about how good a team truly is. 

Unlike Colley, which evaluates the season as a whole, Elo evaluates chronologically. It looks at the ratings *before* a game, calculates an expected outcome, and then updates the ratings based on what actually happened. It can also be configured to care about the Margin of Victory (rewarding blowouts).

### How it Works
1. Everyone starts with a base rating (e.g., 1500).
2. Before a game, the system compares Team A's rating to Team B's rating to calculate a win probability. (If Team A is 1600 and Team B is 1200, Team A is heavily expected to win).
3. The game is played.
4. Ratings are exchanged. If Team A wins as expected, they gain a tiny amount of points. If Team B pulls off a massive upset, Team B steals a huge amount of points from Team A.

### The Math
**Step 1: Expected Win Probability (Bradley-Terry)**
We use the Bradley-Terry logistic curve to determine the probability ($P$) of Team A beating Team B:

$$ P(A) = \frac{1}{1 + 10^{(R_B - R_A) / 400}} $$
*Note: A 400-point difference translates to a team being exactly 10 times more likely to win than lose (about a 91% win probability).*

**Step 2: The Outcome ($S_A$)**
The actual result of the game is converted to a mathematical score representing the share of the win. To properly handle overtime games, the outcome is apportioned as follows:
- **Regulation Win:** $1.0$
- **Overtime Win:** $0.667$ 
- **Overtime Tie:** $0.5$ 
- **Overtime Loss:** $0.333$ 
- **Regulation Loss:** $0.0$

This ensures that forcing a stronger team into overtime correctly rewards the underdog (and slightly penalizes the favorite relative to expectation), even if the underdog ultimately loses.

**Step 3: Margin of Victory Multiplier (MoVM) [Optional]**
If enabled, the system scales the rating exchange based on the goal differential ($GD$). It uses a logarithmic curve so that winning by 10 goals isn't treated as mathematically twice as impressive as winning by 5 goals, discouraging teams from endlessly running up the score.  A user definable cap on goal differential is also implemented.

$$ \text{MoVM} = \ln(|GD| + 1) \times \frac{2.2}{(|R_{\text{winner}} - R_{\text{loser}}| \times 0.001) + 2.2} $$

**Step 4: The Rating Update (Elo)**
Finally, the ratings are updated using the $K$-factor, which dictates how volatile or reactive the system is. A $K$ of 32 is standard.

$$ R_A' = R_A + K \times \text{MoVM} \times (S_A - P(A)) $$
$$ R_B' = R_B + K \times \text{MoVM} \times (S_B - P(B)) $$


**Step 5: Strength of Schedule (SOS)**
Because ratings change over time, a team's SOS is computed by averaging the ratings of their opponents *exactly as they were rated at the time the game was played*.

### Inputs & Outputs
* **Inputs needed:** Chronological game results (including scores if MoVM is enabled), an initial starting rating, a K-factor, and an optional maximum Goal Differential cap.
* **Outputs produced:** A dynamic Power Rating (e.g., 1600) representing their current strength, and a historical SOS.

### Example Calculation - Using Margin of Victory Multiplier __MoVM__

Let's walk through a game where Team A (Rating: 1550) beats Team B (Rating: 1450) in 
regulation with a score of 5-2. We will use a standard $K$-factor of 32.  Remember
that this process is applied to each game in sequence.  The ratings used are the
teams ratings at the start of this game.

**1. Expected Win Probability:**
$$ P(A) = \frac{1}{1 + 10^{(1450 - 1550) / 400}} = \frac{1}{1 + 10^{-0.25}} \approx 0.640 $$
Team A is expected to win 64% of the time. Team B's probability $P(B)$ is $0.360$.

**2. The Outcome:**
Because it was a regulation win, $S_A = 1.0$ and $S_B = 0.0$.

**3. Margin of Victory Multiplier (MoVM):**
The goal differential ($GD$) is $5 - 2 = 3$. The rating difference is 100.
$$ \text{MoVM} = \ln(3 + 1) \times \frac{2.2}{(100 \times 0.001) + 2.2} = 1.386 \times \frac{2.2}{2.3} \approx 1.326 $$

**4. The Rating Update:**
Team A gains points because they won, but the gain is slightly moderated because they were expected to win.
$$ R_A' = 1550 + 32 \times 1.326 \times (1.0 - 0.640) = 1550 + 15.28 = 1565.28 $$
$$ R_B' = 1450 + 32 \times 1.326 \times (0.0 - 0.360) = 1450 - 15.28 = 1434.72 $$

Team A's new rating is ~1565, and Team B's new rating is ~1435.

**Alternative Scenario: The Upset**
Now let's imagine Team B (1450) pulls off an upset and beats Team A (1550) with the same 5-2 score.

**1. Expected Win Probability & MoVM:**
These values remain the same because the rating gap and goal differential are identical. 
$P(A) = 0.640$, $P(B) = 0.360$, and $\text{MoVM} \approx 1.326$.

**2. The Outcome:**
Team B won in regulation, so $S_A = 0.0$ and $S_B = 1.0$.

**3. The Rating Update:**
Team B gains a massive amount of points because they overcame a significant mathematical expectation to win, while Team A is heavily penalized for losing to a weaker opponent.
$$ R_A' = 1550 + 32 \times 1.326 \times (0.0 - 0.640) = 1550 - 27.16 = 1522.84 $$
$$ R_B' = 1450 + 32 \times 1.326 \times (1.0 - 0.360) = 1450 + 27.16 = 1477.16 $$

Team A plummets to ~1523, and Team B surges to ~1477. Notice how the upset (a 27.16 point exchange) causes a much larger swing than the expected win (a 15.28 point exchange) did in the first scenario.

### What if MoVM is Disabled?
If the Margin of Victory Multiplier is turned off, the goal differential is completely ignored, and the $\text{MoVM}$ variable simply becomes $1.0$. The math then relies entirely on the win probability and the outcome.

In the **Expected Win Scenario**:
$$ R_A' = 1550 + 32 \times 1.0 \times (1.0 - 0.640) = 1550 + 11.52 = 1561.52 $$
$$ R_B' = 1450 + 32 \times 1.0 \times (0.0 - 0.360) = 1450 - 11.52 = 1438.48 $$
*(The expected 5-2 win now yields slightly fewer points because the 3-goal margin is no longer rewarded).*

In the **Upset Scenario**:
$$ R_A' = 1550 + 32 \times 1.0 \times (0.0 - 0.640) = 1550 - 20.48 = 1529.52 $$
$$ R_B' = 1450 + 32 \times 1.0 \times (1.0 - 0.360) = 1450 + 20.48 = 1470.48 $$
*(The 5-2 upset penalizes Team A slightly less because the 3-goal deficit is ignored. The only thing that matters is that they lost a game they were expected to win).*



# Summary - Similarities and Differences
Both the Colley Matrix and the Bradley-Terry/Elo Hybrid models are mathematical ranking systems designed to evaluate team performance and establish rankings from a schedule of games. In a segmented league scenario (like one starting with disconnected upper and lower divisions), both models initially face challenges if all teams begin with equal ratings, as they cannot immediately identify the strength gap between the divisions until cross-play begins. However, they diverge fundamentally in their philosophy: the Colley Matrix is a "resume-based" system focused on objective, retrospective fairness, while the Bradley-Terry/Elo model is a "power-based" system designed for predictive accuracy and rapid reactivity.

## Differences Between the Methods

| Feature | Colley Matrix | Bradley-Terry / Elo Hybrid |
| :--- | :--- | :--- |
| **Primary Goal** | Descriptive Fairness (Resume-based) | Predictive Accuracy (Power-based) |
| **Mathematical Approach** | Solves a system of linear equations across the whole season simultaneously. | Game-by-game chronological updates based on the expected probability of an outcome. |
| **Sequence Dependency** | **Independent:** It does not matter *when* an upset or game occurred during the season. | **Dependent:** Beating a top team team early in the season is worth less than beating them later in the season when their rating is higher. |
| **Margin of Victory** | Deliberately ignored to prevent teams from running up the score. | Easily extensible to include a Margin of Victory Multiplier (MoVM). |
| **Initial Ratings** | Every team starts mathematically equal; zero initial bias. | Requires setting starting ratings; adjusting starting ratings for divisions introduces human bias. |
| **Handling Missed Matchups** | Excels at inferring gaps (e.g., 1st vs 12th) through common opponents without penalizing teams. | Stratifies quickly once cross-play begins by funneling points between divisions. |
| **Best Used For** | Playoff seeding (easier to defend, rewards winning the games on your schedule). | Setting Vegas betting lines or measuring pure, current team power. |