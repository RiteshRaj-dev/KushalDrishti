# Measuring results (fills the blanks on slides 2 and 4)
Nothing in this repo contains invented accuracy numbers. Measure on footage you are allowed to use (your own, or freely licensed).
```
python -m kd_edge.evaluate prepare --video classroom.mp4 --folder eval_frames --n 40
# open eval_frames/, fill true_headcount and a 1 or 0 for every equipment column in ground_truth.csv
python -m kd_edge.evaluate run --folder eval_frames --claimed 18 --out outputs
python -m kd_edge.speed --image eval_frames/<one frame>.jpg --out outputs
python tools/fill_deck.py deck/SIH26245.pptx SIH26245_filled.pptx --accuracy outputs/accuracy_table.csv \
    --summary outputs/evaluation_summary.json --speed outputs/speed_report.json --video https://youtu.be/YOUR_LINK
```
Scoring: per frame. A person found counts as a true positive, an extra detection as a false positive, a miss as a false negative. Equipment is scored as seen or not seen per frame. Attendance mismatch compares the flag from the model count with the flag from your true count.
Say on the slide where the numbers were measured (video, number of frames, machine).
