clear
f= @(x,xdata)x(1)*(1-exp(-x(2)*xdata))+x(3)*(1-exp(-x(4)*xdata))

files = dir('./*.csv');
fullpaths = fullfile({files.folder}, {files.name});
x0=[0.01 ,  0.02,  0.01,  0.003];
% options = optimoptions(@lsqnonlin,'Algorithm','trust-region-reflective');
figure;hold on;
for i=1:length(files)
    cell{i}=readtable(fullpaths{i});
    xdata=table2array(cell{i}(:,1));
    ydata=table2array(cell{i}(:,2));
    scatter(xdata,ydata,'.')
    x = lsqcurvefit(f,x0,xdata,ydata);
%     x = lsqnonlin(f,x0,xdata,ydata,options)
    xx(i,:)=x;


end

% 
% xdata=interval0points.VarName1;
% ydata=interval0points.VarName2;
% 
% x = lsqcurvefit(f,x0,xdata,ydata)

% function relax