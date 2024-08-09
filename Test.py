def calNumberArray(input_list):
    if input_list.len() != 8:
        return -1
    outputData = 0
    for i in range(8):
        data = input_list[i] - 48
        multiData = 10**(7-i)
        outputData = outputData + data*multiData
    return outputData


