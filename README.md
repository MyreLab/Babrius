<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MyreLab/Babrius/counter-assets/clock-dark.svg">
  <img alt="Elapsed time" src="https://raw.githubusercontent.com/MyreLab/Babrius/counter-assets/clock-light.svg" width="480">
</picture>

## How to run

```
python3 -m unittest discover -s tests
CLOCK_START=2020-01-15T09:30:00 CLOCK_TZ=America/Los_Angeles python3 counter.py --cards out
```
