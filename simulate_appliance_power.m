% simulate_appliance_power.m
% Load appliance power data and build/run a Simulink model with the original timestamps.
% Run this script in MATLAB from the repository root.

clearvars;
close all;
clc;

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

% Build a relative time vector in seconds for Simulink time base
startTime = tbl.TimeStamp(1);
timeSeconds = seconds(tbl.TimeStamp - startTime);
timeSeconds = double(timeSeconds);

% Create timeseries signals for each appliance
ts_WashingMachine = timeseries(tbl.WashingMachine_Power, timeSeconds, 'Name', 'WashingMachine');
ts_Heater = timeseries(tbl.Heater_Power, timeSeconds, 'Name', 'Heater');
ts_AC = timeseries(tbl.AC_Power, timeSeconds, 'Name', 'AC');
ts_VehicleCharger = timeseries(tbl.VehicleCharger_Power, timeSeconds, 'Name', 'VehicleCharger');
ts_VacuumCleaner = timeseries(tbl.VacuumCleaner_Power, timeSeconds, 'Name', 'VacuumCleaner');

for ts = {ts_WashingMachine, ts_Heater, ts_AC, ts_VehicleCharger, ts_VacuumCleaner}
    ts{1}.TimeInfo.Units = 'seconds';
end

% Create or replace the Simulink model
modelName = 'SimulateAppliancePower';
if bdIsLoaded(modelName)
    close_system(modelName, 0);
end
new_system(modelName);
open_system(modelName);
set_param(modelName, 'Solver', 'ode45', 'StartTime', '0', 'StopTime', num2str(timeSeconds(end)), 'SaveOutput', 'on', 'SaveFormat', 'StructureWithTime');

% Layout positions
xFrom = 30;
xTo = 260;
y0 = 30;
yStep = 90;

appliances = {
    'WashingMachine', 'ts_WashingMachine', 'WashingMachine_Out';
    'Heater', 'ts_Heater', 'Heater_Out';
    'AC', 'ts_AC', 'AC_Out';
    'VehicleCharger', 'ts_VehicleCharger', 'VehicleCharger_Out';
    'VacuumCleaner', 'ts_VacuumCleaner', 'VacuumCleaner_Out';
};

% Add From Workspace and To Workspace blocks for each appliance
for i = 1:size(appliances, 1)
    name = appliances{i, 1};
    dataVar = appliances{i, 2};
    outputVar = appliances{i, 3};
    yPos = y0 + (i-1) * yStep;

    fromBlock = add_block('simulink/Sources/From Workspace', [modelName '/' name]);
    set_param(fromBlock, 'VariableName', dataVar, 'SampleTime', '-1', 'Position', [xFrom yPos xFrom+130 yPos+40]);

    toBlock = add_block('simulink/Sinks/To Workspace', [modelName '/' outputVar]);
    set_param(toBlock, 'VariableName', outputVar, 'SaveFormat', 'StructureWithTime', 'Position', [xTo yPos xTo+120 yPos+40]);

    add_line(modelName, [name '/1'], [outputVar '/1'], 'autorouting', 'on');
end

% Save the model file
save_system(modelName);

% Run the Simulink simulation
simOut = sim(modelName, 'ReturnWorkspaceOutputs', 'on');

% Reconstruct datetime signal axis from the original timestamps
simTime = simOut.WashingMachine_Out.time;
plotTime = startTime + seconds(simTime);

% Plot the simulated appliance power values
figure('Name', 'Appliance Power Simulation', 'NumberTitle', 'off');
plot(plotTime, simOut.WashingMachine_Out.signals.values, '-o');
hold on;
plot(plotTime, simOut.Heater_Out.signals.values, '-x');
plot(plotTime, simOut.AC_Out.signals.values, '-s');
plot(plotTime, simOut.VehicleCharger_Out.signals.values, '-d');
plot(plotTime, simOut.VacuumCleaner_Out.signals.values, '-^');

xlabel('Timestamp');
ylabel('Power (kW)');
title('Simulated Appliance Power Using Original Timestamps');
legend('Washing Machine', 'Heater', 'AC', 'Vehicle Charger', 'Vacuum Cleaner', 'Location', 'best');
grid on;

% Save the figure for review
saveas(gcf, fullfile(pwd, 'appliance_power_simulation.png'));

fprintf('Simulink model created: %s\n', which([modelName '.slx']));
fprintf('Simulation completed. Plot saved to appliance_power_simulation.png\n');
