#CFB Tools

A repository to contain any work related to NCAA football.

## Polls

Contains scripts for scraping both the AP Poll and r/CFB Poll ballots for a
given week.  Also a script to do some simple analysis of poll results, including
a visualization of the votes broken down by team.

## Website

Planning to put a lot of this content on my ajseventeen.tech site.  The proposed
directory structure:

```
+ /cfb
|-- styles.css
|-+ /polls
| |-+ /ap
| | |-+ /year
| |   |-- index.html (summary)
| |   |-+ /week
| |     |-- index.html (visualization)
| |     |-- raw.csv
| |-+ /rcfb
|   |-+ /year
|     |-+ /week
|       |-- index.html (visualization)
|       |-- raw.csv
```
