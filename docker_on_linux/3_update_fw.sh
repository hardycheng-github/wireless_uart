#!/bin/bash

file="shares/fw_lastest/esptool.sh"
tempfile="temp.sh"

searchString="--port"
original_port=""

while IFS=' ' read -r param value; do
    if [[ "$param" == "--port" ]]; then
        original_port="$value"
    fi
done < "$file"

if [[ -z "$original_port" ]]; then
    echo "esptool script not found..."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "original port=$original_port"
read -p "Enter new port (e.g., /dev/ttyUSB0): " new_port

if [[ -n "$new_port" ]]; then
    # 替换 --port 参数内容为新端口
    while IFS= read -r line; do
        echo "${line//$original_port/$new_port}"
    done < "$file" > "$tempfile"
    
    mv "$tempfile" "$file"
    
    echo "Port updated successfully."
fi

echo "Start update firmware..."

bash "$file"