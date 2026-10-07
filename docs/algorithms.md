**Prepared for**: MHC Rankings and Standings Committee

**Prepared by:** *Brad Campbell*

**Date**: Jun 17, 2026

---

# Ranking Algorithms Explanation

The rankings program uses the **Colley Matrix** method to rank teams.

This document explains the philosophy behind the method, the mathematical equations powering it, and the step-by-step process used to calculate the final rankings.

---

## How the Rankings Work, in Plain Language

The Colley method gives every team a rating from 0 to 1 based only on who they played and whether they won. Every team starts at 0.500, which means average. Wins push a rating up and losses push it down. The score of the game does not matter: a 1-0 win counts the same as a 10-0 win, so there is no reason to run up the score. A win or loss in overtime counts a little less than one in regulation.

| Result                    | Share of a point |
|---------------------------|:----------------:|
| Regulation win            | 1.000            |
| Overtime win              | 0.667            |
| Tie (decided in overtime) | 0.500            |
| Overtime loss             | 0.333            |
| Regulation loss           | 0.000            |

What makes it fair is that a win is worth more against a strong team than against a weak one. A team's rating depends on its opponents' ratings, and each opponent's rating depends on theirs. The computer works through all of these links at once and settles on one set of ratings where everything fits together. That is why a team can move up the rankings without playing, if a team it beat keeps winning.

**Strength of schedule (SOS)** is the average rating of the teams a team has played. A higher number means a tougher schedule. A team with a modest record and a high SOS may have faced harder opponents than a team with a better record and a low SOS.

*Example:* Team A and Team B each finish 1-1. Team A's win was over the league's best team. Team B's win was over the league's weakest team. Team A gets the higher rating, because its win was harder to earn.

<details>
<summary>Technical details</summary>

## The Colley Matrix Method

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

</details>
