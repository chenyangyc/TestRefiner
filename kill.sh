#!/bin/bash

# Find all processes with 'process' in their name, excluding the grep command itself
pids=$(ps aux | grep 'setup' | awk '{print $2}')

# Check if any processes were found
if [ -z "$pids" ]; then
  echo "No processes found with 'process' in their name."
  exit 0
fi

# Kill each found process
for pid in $pids; do
  echo "Killing process with PID $pid"
  kill -9 $pid
done

echo "All processes with 'process' in their name have been killed."


#!/bin/bash

# Find all processes with 'process' in their name, excluding the grep command itself
pids=$(ps aux | grep 'd4j' | awk '{print $2}')

# Check if any processes were found
if [ -z "$pids" ]; then
  echo "No processes found with 'process' in their name."
  exit 0
fi

# Kill each found process
for pid in $pids; do
  echo "Killing process with PID $pid"
  kill -9 $pid
done

echo "All processes with 'process' in their name have been killed."



# Find all processes with 'process' in their name, excluding the grep command itself
pids=$(ps aux | grep 'defects' | awk '{print $2}')

# Check if any processes were found
if [ -z "$pids" ]; then
  echo "No processes found with 'process' in their name."
  exit 0
fi

# Kill each found process
for pid in $pids; do
  echo "Killing process with PID $pid"
  kill -9 $pid
done

echo "All processes with 'process' in their name have been killed."


# defects4j checkout -p Math -v 106f -w /data/defects4j/projects_0728/Math_106/fixed
# defects4j checkout -p Lang -v 65f -w /data/defects4j/projects_0728/Lang_65/fixed
# defects4j checkout -p Closure -v 176f -w /data/defects4j/projects_0728/Closure_176/fixed
# defects4j checkout -p Chart -v 26f -w /data/defects4j/projects_0728/Chart_26/fixed
# defects4j checkout -p Time -v 27f -w /data/defects4j/projects_0728/Time_27/fixed