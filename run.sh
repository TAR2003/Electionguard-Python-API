#!/bin/bash
# Script to run oneconnectionsingleelection.py in parallel for specific n values

# Array of n values
values=(1 5 9 13 17 21)

# Loop over the array
for i in "${values[@]}"; do
    for i in {1..5}; do
        python ./oneconnectionsingleelection.py > output_$i.log 2>&1 &
    done
    wait
    echo "Starting oneconnectionsingleelection.py with n=$i ..."
    python ./oneconnectionsingleelection.py "$i" > output_"$i".log 2>&1 &
done

# Wait for all background jobs to finish
wait
echo "All processes completed."
