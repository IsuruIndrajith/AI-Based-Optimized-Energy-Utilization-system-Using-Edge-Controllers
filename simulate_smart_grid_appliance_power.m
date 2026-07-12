% simulate_smart_grid_appliance_power.m
% Load appliance power data and create a Smart Grid-style Simulink/Simscape model.
% Uses the original timestamps to build time series for appliance loads.
% Run this script in MATLAB from the repository root.

clearvars;
close all;
clc;

% Detect whether Simscape and Simscape Electrical are available
haveSimscape = license('test', 'Simscape') && license('test', 'Simscape_Electrical');
if ~haveSimscape
    warning(['Simscape and Simscape Electrical are not available. ', ...
             'Falling back to a standard Simulink load playback model.']);
end

% Path to the CSV file
dataFolder = fullfile(pwd, 'data');
csvFile = fullfile(dataFolder, 'appliance_power_data.csv');

if ~isfile(csvFile)
    error('CSV file not found: %s', csvFile);
end

% Read the data and parse timestamps
opts = detectImportOptions(csvFile, 'NumHeaderLines', 0);
opts = setvartype(opts, 'TimeStamp', 'char');

tbl = readtable(csvFile, opts);
if isempty(tbl)
    error('No data found in %s', csvFile);
end

% Convert TimeStamp strings to datetime and sort by time
try
    tbl.TimeStamp = datetime(tbl.TimeStamp, 'InputFormat', 'MM/dd/yyyy HH:mm', 'Locale', 'en_US');
catch
    tbl.TimeStamp = datetime(tbl.TimeStamp, 'InputFormat', 'MM/dd/yyyy HH:mm');
end

tbl = sortrows(tbl, 'TimeStamp');

% Convert appliance power columns to numeric and validate values
powerCols = {'WashingMachine_Power', 'Heater_Power', 'AC_Power', 'VehicleCharger_Power', 'VacuumCleaner_Power'};
for i = 1:numel(powerCols)
    col = powerCols{i};
    rawValues = string(tbl.(col));
    numericValues = str2double(rawValues);

    if any(isnan(numericValues))
        badRows = find(isnan(numericValues));
        warning('Found %d invalid values in column %s. Replacing them with 0.', numel(badRows), col);
        badValues = rawValues(badRows);
        disp(table(badRows(:), badValues(:), 'VariableNames', {'InvalidRow', 'RawValue'}));
        numericValues(isnan(numericValues)) = 0;
    end

    if any(isinf(numericValues))
        error('Infinite values found in column %s. Please clean or convert the CSV data.', col);
    end

    tbl.(col) = numericValues;
end

% Build a relative time vector in seconds for Simulink time base
startTime = tbl.TimeStamp(1);
timeSeconds = seconds(tbl.TimeStamp - startTime);
timeSeconds = double(timeSeconds);

% Create timeseries signals for each appliance power profile
P_WashingMachine = timeseries(tbl.WashingMachine_Power, timeSeconds, 'Name', 'P_WashingMachine');
P_Heater = timeseries(tbl.Heater_Power, timeSeconds, 'Name', 'P_Heater');
P_AC = timeseries(tbl.AC_Power, timeSeconds, 'Name', 'P_AC');
P_VehicleCharger = timeseries(tbl.VehicleCharger_Power, timeSeconds, 'Name', 'P_VehicleCharger');
P_VacuumCleaner = timeseries(tbl.VacuumCleaner_Power, timeSeconds, 'Name', 'P_VacuumCleaner');

P_WashingMachine.TimeInfo.Units = 'seconds';
P_Heater.TimeInfo.Units = 'seconds';
P_AC.TimeInfo.Units = 'seconds';
P_VehicleCharger.TimeInfo.Units = 'seconds';
P_VacuumCleaner.TimeInfo.Units = 'seconds';

% Also create array inputs for fallback Simulink From Workspace blocks
P_WashingMachine_Array = [timeSeconds(:), tbl.WashingMachine_Power(:)];
P_Heater_Array = [timeSeconds(:), tbl.Heater_Power(:)];
P_AC_Array = [timeSeconds(:), tbl.AC_Power(:)];
P_VehicleCharger_Array = [timeSeconds(:), tbl.VehicleCharger_Power(:)];
P_VacuumCleaner_Array = [timeSeconds(:), tbl.VacuumCleaner_Power(:)];

assignin('base', 'P_WashingMachine', P_WashingMachine);
assignin('base', 'P_Heater', P_Heater);
assignin('base', 'P_AC', P_AC);
assignin('base', 'P_VehicleCharger', P_VehicleCharger);
assignin('base', 'P_VacuumCleaner', P_VacuumCleaner);
assignin('base', 'P_WashingMachine_Array', P_WashingMachine_Array);
assignin('base', 'P_Heater_Array', P_Heater_Array);
assignin('base', 'P_AC_Array', P_AC_Array);
assignin('base', 'P_VehicleCharger_Array', P_VehicleCharger_Array);
assignin('base', 'P_VacuumCleaner_Array', P_VacuumCleaner_Array);

% Create current timeseries only if Simscape is available
if haveSimscape
    nominalVoltage = 230; % Volts (RMS)
    I_WashingMachine = timeseries(tbl.WashingMachine_Power * 1000 / nominalVoltage, timeSeconds, 'Name', 'I_WashingMachine');
    I_Heater = timeseries(tbl.Heater_Power * 1000 / nominalVoltage, timeSeconds, 'Name', 'I_Heater');
    I_AC = timeseries(tbl.AC_Power * 1000 / nominalVoltage, timeSeconds, 'Name', 'I_AC');
    I_VehicleCharger = timeseries(tbl.VehicleCharger_Power * 1000 / nominalVoltage, timeSeconds, 'Name', 'I_VehicleCharger');
    I_VacuumCleaner = timeseries(tbl.VacuumCleaner_Power * 1000 / nominalVoltage, timeSeconds, 'Name', 'I_VacuumCleaner');

    I_WashingMachine.TimeInfo.Units = 'seconds';
    I_Heater.TimeInfo.Units = 'seconds';
    I_AC.TimeInfo.Units = 'seconds';
    I_VehicleCharger.TimeInfo.Units = 'seconds';
    I_VacuumCleaner.TimeInfo.Units = 'seconds';

    assignin('base', 'I_WashingMachine', I_WashingMachine);
    assignin('base', 'I_Heater', I_Heater);
    assignin('base', 'I_AC', I_AC);
    assignin('base', 'I_VehicleCharger', I_VehicleCharger);
    assignin('base', 'I_VacuumCleaner', I_VacuumCleaner);
end

% Create/replace the Simulink model
if haveSimscape
    modelName = 'SmartGridApplianceSimulation';
else
    modelName = 'SmartGridApplianceSimulationFallback';
end
if bdIsLoaded(modelName)
    close_system(modelName, 0);
end
new_system(modelName);
open_system(modelName);
set_param(modelName, 'StartTime', '0', 'StopTime', num2str(timeSeconds(end)), 'SaveOutput', 'on', 'SaveFormat', 'StructureWithTime');

if haveSimscape
    set_param(modelName, 'Solver', 'ode23tb');
    
    % Layout coordinates
    xStart = 30;
    nodeX = 200;
    appX = 420;
    outX = 620;
    y0 = 40;
    yStep = 90;
    
    % Add required library blocks
    add_block('powerlib/Powergui', [modelName '/Powergui'], 'Position', [xStart y0 xStart+80 y0+60]);
    voltageSource = add_block('powerlib/Sources/AC Voltage Source', [modelName '/GridVoltage'], 'Position', [xStart y0+110 xStart+120 y0+170]);
    set_param(voltageSource, 'Amplitude', '230', 'Frequency', '50');
    add_block('simscape/Foundation Library/Electrical/Electrical Elements/Electrical Reference', [modelName '/Electrical Reference'], 'Position', [xStart y0+270 xStart+60 y0+310]);
    add_block('powerlib/Measurements/Voltage Measurement', [modelName '/BusVoltageMeasurement'], 'Position', [nodeX-80 y0+110 nodeX-20 y0+170]);
    add_block('simscape/Utilities/PS-Simulink Converter', [modelName '/BusVoltageToSimulink'], 'Position', [outX y0+110 outX+80 y0+170]);
    toWorkspaceVoltage = add_block('simulink/Sinks/To Workspace', [modelName '/BusVoltage'], 'Position', [outX+120 y0+110 outX+240 y0+170]);
    set_param(toWorkspaceVoltage, 'VariableName', 'BusVoltage', 'SaveFormat', 'StructureWithTime');
    add_line(modelName, 'BusVoltageMeasurement/1', 'BusVoltageToSimulink/1', 'autorouting', 'on');
    add_line(modelName, 'BusVoltageToSimulink/1', 'BusVoltage/1', 'autorouting', 'on');
    add_line(modelName, 'GridVoltage/1', 'BusVoltageMeasurement/1', 'autorouting', 'on');
    add_line(modelName, 'GridVoltage/2', 'Electrical Reference/1', 'autorouting', 'on');
    add_line(modelName, 'BusVoltageMeasurement/2', 'Electrical Reference/1', 'autorouting', 'on');
    
    appliances = {
        'Washing Machine', 'I_WashingMachine';
        'Heater', 'I_Heater';
        'AC', 'I_AC';
        'Vehicle Charger', 'I_VehicleCharger';
        'Vacuum Cleaner', 'I_VacuumCleaner';
    };
    
    for i = 1:size(appliances, 1)
        yPos = y0 + 220 + (i-1) * yStep;
        fromName = sprintf('From_%d', i);
        convName = sprintf('S2P_%d', i);
        curName = sprintf('Controlled_I_%d', i);

        fromBlock = add_block('simulink/Sources/From Workspace', [modelName '/' fromName], 'Position', [xStart yPos xStart+130 yPos+40]);
        set_param(fromBlock, 'VariableName', appliances{i, 2}, 'SampleTime', '-1');

        add_block('simscape/Utilities/Simulink-PS Converter', [modelName '/' convName], 'Position', [nodeX yPos xStart+300 yPos+40]);
        add_block('simscape/Foundation Library/Electrical/Electrical Sources/Controlled Current Source', [modelName '/' curName], 'Position', [appX yPos appX+120 yPos+60]);

        add_line(modelName, [fromName '/1'], [convName '/1'], 'autorouting', 'on');
        add_line(modelName, [convName '/1'], [curName '/1'], 'autorouting', 'on');
        add_line(modelName, [curName '/+'], 'BusVoltageMeasurement/1', 'autorouting', 'on');
        add_line(modelName, [curName '/-'], 'Electrical Reference/1', 'autorouting', 'on');
    end
else
    set_param(modelName, 'Solver', 'ode45');
    
    % Layout coordinates for fallback model
    xStart = 30;
    sumX = 320;
    outX = 520;
    y0 = 40;
    yStep = 80;

    sumBlock = add_block('simulink/Math Operations/Sum', [modelName '/TotalLoadSum'], 'Position', [sumX y0+20 sumX+80 y0+80]);
    set_param(sumBlock, 'Inputs', '+++++');

    appliances = {
        'WashingMachine', 'P_WashingMachine';
        'Heater', 'P_Heater';
        'AC', 'P_AC';
        'VehicleCharger', 'P_VehicleCharger';
        'VacuumCleaner', 'P_VacuumCleaner';
    };

    for i = 1:size(appliances, 1)
        yPos = y0 + (i-1) * yStep;
        fromName = sprintf('From_%d', i);
        toName = sprintf('%s_Out', appliances{i, 1});

        fromBlock = add_block('simulink/Sources/From Workspace', [modelName '/' fromName], 'Position', [xStart yPos xStart+130 yPos+40]);
        set_param(fromBlock, 'VariableName', [appliances{i, 2} '_Array'], 'SampleTime', '-1');

        toBlock = add_block('simulink/Sinks/To Workspace', [modelName '/' toName], 'Position', [outX yPos outX+120 yPos+40]);
        set_param(toBlock, 'VariableName', [appliances{i, 1} '_Out'], 'SaveFormat', 'StructureWithTime');

        add_line(modelName, [fromName '/1'], [toName '/1'], 'autorouting', 'on');
        add_line(modelName, [fromName '/1'], ['TotalLoadSum/' num2str(i)], 'autorouting', 'on');
    end

    totalOut = add_block('simulink/Sinks/To Workspace', [modelName '/TotalLoad_Out'], 'Position', [outX y0+5 outX+120 y0+45]);
    set_param(totalOut, 'VariableName', 'TotalLoad', 'SaveFormat', 'StructureWithTime');
    add_line(modelName, 'TotalLoadSum/1', 'TotalLoad_Out/1', 'autorouting', 'on');
end

% Save and run the model
save_system(modelName);
simOut = sim(modelName, 'ReturnWorkspaceOutputs', 'on');

% Plot results from the original kW dataset with bus voltage
figure('Name', 'Smart Grid Appliance Load Simulation', 'NumberTitle', 'off');
plot(tbl.TimeStamp, tbl.WashingMachine_Power, '-o');
hold on;
plot(tbl.TimeStamp, tbl.Heater_Power, '-x');
plot(tbl.TimeStamp, tbl.AC_Power, '-s');
plot(tbl.TimeStamp, tbl.VehicleCharger_Power, '-d');
plot(tbl.TimeStamp, tbl.VacuumCleaner_Power, '-^');
if isfield(simOut, 'BusVoltage')
    timeVoltage = startTime + seconds(simOut.BusVoltage.time);
    plot(timeVoltage, abs(simOut.BusVoltage.signals.values), '--', 'LineWidth', 1.2);
    legend('Washing Machine', 'Heater', 'AC', 'Vehicle Charger', 'Vacuum Cleaner', 'Bus Voltage');
else
    legend('Washing Machine', 'Heater', 'AC', 'Vehicle Charger', 'Vacuum Cleaner');
end

xlabel('Timestamp');
ylabel('Power (kW) / Voltage (V)');
title('Smart Grid Appliance Load Simulation with Original Timestamps');
grid on;
saveas(gcf, fullfile(pwd, 'smart_grid_appliance_simulation.png'));

fprintf('Smart Grid simulation model created: %s\n', which([modelName '.slx']));
fprintf('Simulation completed. Plot saved to smart_grid_appliance_simulation.png\n');

% Extract simulated appliance power data and save to CSV
fprintf('\n--- Saving simulated data to CSV ---\n');

% Extract the simulated power outputs from the simulation results
simulatedWashingMachine = simOut.WashingMachine_Out.signals.values;
simulatedHeater = simOut.Heater_Out.signals.values;
simulatedAC = simOut.AC_Out.signals.values;
simulatedVehicleCharger = simOut.VehicleCharger_Out.signals.values;
simulatedVacuumCleaner = simOut.VacuumCleaner_Out.signals.values;
simTime = simOut.WashingMachine_Out.time;

% Create timestamps for simulated output based on simulation time
simTimeStamps = startTime + seconds(simTime);

% Create output table with simulated timestamps and power values
simDataTable = table(simTimeStamps, simulatedWashingMachine, simulatedHeater, ...
    simulatedAC, simulatedVehicleCharger, simulatedVacuumCleaner, ...
    'VariableNames', {'TimeStamp', 'WashingMachine_Power', 'Heater_Power', ...
    'AC_Power', 'VehicleCharger_Power', 'VacuumCleaner_Power'});

% Save to CSV file
outputCsvFile = fullfile(pwd, 'data', 'appliance_power_data_simulated.csv');
writetable(simDataTable, outputCsvFile);

fprintf('Simulated data saved to: %s\n', outputCsvFile);
fprintf('Total rows: %d\n', height(simDataTable));
fprintf('Columns: %s\n', strjoin(simDataTable.Properties.VariableNames, ', '));
