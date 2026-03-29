var app = angular.module('HistogramApp', ['ngMaterial', 'ngMessages']);

// Define Cooper Union Theme
app.config(function ($mdThemingProvider) {
    var cooperMaroon = $mdThemingProvider.extendPalette('red', {
        '500': '#990000', // Cooper Union primary brand color
        'contrastDefaultColor': 'light'
    });

    $mdThemingProvider.definePalette('cooperMaroon', cooperMaroon);

    $mdThemingProvider.theme('default')
        .primaryPalette('cooperMaroon')
        .accentPalette('amber');
});

// File Upload Directive
app.directive('fileModel', ['$parse', function ($parse) {
    return {
        restrict: 'A',
        link: function (scope, element, attrs) {
            var model = $parse(attrs.fileModel);
            var modelSetter = model.assign;

            element.bind('change', function () {
                scope.$apply(function () {
                    modelSetter(scope, element[0].files[0]);
                });
            });
        }
    };
}]);

app.controller('MainController', function ($scope, $http, $mdToast, $interval) {
    $scope.isLoggedIn = false;
    $scope.username = "";
    $scope.loginData = {};

    $scope.availableFiles = [];
    $scope.equalizedFiles = [];
    $scope.connectedNodes = [];
    $scope.logs = [];
    $scope.processingImages = {};
    $scope.upload = {}; // Wrap in object to avoid ng-if child scope shadowing
    $scope.uploading = false;

    // Simple mock login
    $scope.login = function () {
        if ($scope.loginData.username && $scope.loginData.password) {
            $scope.isLoggedIn = true;
            $scope.username = $scope.loginData.username;
            $scope.refreshFiles();
            $scope.refreshNodes();
        }
    };

    $scope.logout = function () {
        $scope.isLoggedIn = false;
        $scope.username = "";
        $scope.loginData = {};
    };

    $scope.showToast = function (message) {
        $mdToast.show(
            $mdToast.simple()
                .textContent(message)
                .position('bottom right')
                .hideDelay(3000)
        );
    };

    $scope.hasProcessingImages = function () {
        return Object.values($scope.processingImages).some(val => val === true);
    };

    $scope.getEqualizedName = function (filename) {
        if (!filename) return "";
        var parts = filename.split('.');
        var ext = parts.pop();
        return parts.join('.') + '_equalized.' + ext;
    };

    $scope.refreshNodes = function () {
        $http.get('/nodes').then(function (response) {
            $scope.connectedNodes = response.data.connected_workers;
        }, function (error) {
            console.error("Error fetching nodes", error);
        });
    };

    $scope.refreshLogs = function () {
        $http.get('/logs').then(function (response) {
            $scope.logs = response.data.logs;
        }, function (error) {
            console.error("Error fetching logs", error);
        });
    };

    // Auto-scroll log console
    $scope.$watchCollection('logs', function (newVal, oldVal) {
        if (newVal !== oldVal) {
            setTimeout(function () {
                var consoleDiv = document.getElementById('logConsole');
                if (consoleDiv) {
                    consoleDiv.scrollTop = consoleDiv.scrollHeight;
                }
            }, 50);
        }
    });

    // Auto-refresh cluster status
    $interval(function () {
        if ($scope.isLoggedIn) {
            $scope.refreshNodes();
            $scope.refreshLogs();
        }
    }, 2000);

    $scope.refreshFiles = function () {
        $http.get('/files').then(function (response) {
            $scope.availableFiles = response.data.files;
        });
        $http.get('/files/equalized').then(function (response) {
            $scope.equalizedFiles = response.data.files;
        });
    };

    $scope.uploadFile = function () {
        var file = $scope.upload.myFile;
        if (!file) {
            $scope.showToast("Please select a file first.");
            return;
        }

        var fd = new FormData();
        fd.append('file', file);

        $scope.uploading = true;
        $http.post('/upload', fd, {
            transformRequest: angular.identity,
            headers: { 'Content-Type': undefined }
        })
            .then(function (response) {
                $scope.uploading = false;
                $scope.showToast("File uploaded successfully.");
                $scope.refreshFiles();
            }, function (error) {
                $scope.uploading = false;
                $scope.showToast("Error uploading file: " + (error.data.detail || error.statusText));
            });
    };

    $scope.processImage = function (filename) {
        if ($scope.connectedNodes.length === 0) {
            $scope.showToast("Warning: No worker nodes connected. Master will process this locally.");
        }

        $scope.processingImages[filename] = true;
        $http.post('/process/' + filename).then(function (response) {
            $scope.showToast("Processing job started for " + filename);
            // Polling for completion
            var checkInterval = setInterval(function () {
                $http.get('/files/equalized').then(function (res) {
                    var isDone = res.data.files.some(f => f.name.includes(filename.split('.')[0] + '_equalized'));
                    if (isDone) {
                        clearInterval(checkInterval);
                        $scope.processingImages[filename] = false;
                        $scope.refreshFiles();
                        $scope.showToast("Equalization complete for " + filename);
                    }
                });
            }, 2000);
        }, function (error) {
            $scope.processingImages[filename] = false;
            console.error("Error starting processing", error);
            $scope.showToast("Processing failed: " + (error.data.detail || "Unknown error"));
        });
    };

    $scope.deleteFile = function (filename) {
        if (confirm("Are you sure you want to permanently delete '" + filename + "' and its processed outputs?")) {
            $http.delete('/files/' + filename).then(function (response) {
                $scope.showToast("Deleted " + filename);
                $scope.refreshFiles();
            }, function (error) {
                console.error("Error deleting file", error);
                $scope.showToast("Failed to delete file: " + (error.data.detail || "Unknown error"));
            });
        }
    };

    $scope.deleteProcessedFile = function (filename) {
        if (confirm("Are you sure you want to delete the processed result '" + filename + "'?")) {
            $http.delete('/files/' + filename).then(function (response) {
                $scope.showToast("Deleted " + filename);
                $scope.refreshFiles();
            }, function (error) {
                console.error("Error deleting processed file", error);
                $scope.showToast("Failed to delete processed file: " + (error.data.detail || "Unknown error"));
            });
        }
    };

});
