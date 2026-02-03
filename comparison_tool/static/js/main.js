// Pest Comparison Tool - Main JavaScript

document.addEventListener('DOMContentLoaded', function () {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const previewImage = document.getElementById('previewImage');
    const compareBtn = document.getElementById('compareBtn');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const baselineOutput = document.getElementById('baselineOutput');
    const adcdfOutput = document.getElementById('adcdfOutput');
    const detectionInfo = document.getElementById('detectionInfo');
    const confidenceLevel = document.getElementById('confidenceLevel');
    const confidenceValue = document.getElementById('confidenceValue');
    const exportBtn = document.getElementById('exportBtn');
    const timestamp = document.getElementById('timestamp');

    let selectedFile = null;

    // Upload area click handler
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change handler
    fileInput.addEventListener('change', (e) => {
        handleFileSelect(e.target.files[0]);
    });

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            handleFileSelect(file);
        }
    });

    // Handle file selection
    function handleFileSelect(file) {
        if (!file) return;

        selectedFile = file;

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            uploadArea.classList.add('has-image');
            compareBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    // Compare button click handler
    compareBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        // Show loading
        loading.classList.remove('hidden');
        results.classList.add('hidden');
        compareBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('image', selectedFile);

            const response = await fetch('/api/compare', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                displayResults(data);
            } else {
                alert('错误: ' + (data.error || '未知错误'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('请求失败: ' + error.message);
        } finally {
            loading.classList.add('hidden');
            compareBtn.disabled = false;
        }
    });

    // Display comparison results
    function displayResults(data) {
        // Show results section
        results.classList.remove('hidden');

        // Display baseline LLM result
        if (data.baseline) {
            baselineOutput.textContent = data.baseline.response || '无响应';
        }

        // Display ADCDF result
        if (data.adcdf) {
            adcdfOutput.textContent = data.adcdf.response || '无响应';

            // Show detection image if available
            const detectionImageContainer = document.getElementById('detectionImageContainer');
            const detectionImage = document.getElementById('detectionImage');

            if (data.adcdf.detection_image_url && detectionImageContainer && detectionImage) {
                detectionImage.src = data.adcdf.detection_image_url;
                detectionImageContainer.classList.remove('hidden');
            } else if (detectionImageContainer) {
                detectionImageContainer.classList.add('hidden');
            }

            // Show confidence if detections exist
            if (data.adcdf.detections && data.adcdf.detections.length > 0) {
                const avgConfidence = data.adcdf.detections.reduce((sum, d) => sum + d.confidence, 0) / data.adcdf.detections.length;
                detectionInfo.classList.remove('hidden');
                confidenceLevel.style.width = `${avgConfidence}%`;
                confidenceValue.textContent = `${avgConfidence.toFixed(1)}%`;
            } else {
                detectionInfo.classList.add('hidden');
            }
        }

        // Update timestamp
        if (data.timestamp) {
            const date = new Date(data.timestamp);
            timestamp.textContent = `分析时间: ${date.toLocaleString('zh-CN')}`;
        }

        // Scroll to results
        results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Export button click handler
    exportBtn.addEventListener('click', () => {
        exportComparison();
    });

    // Export comparison as image
    async function exportComparison() {
        // Use html2canvas if available, otherwise provide instructions
        if (typeof html2canvas === 'undefined') {
            // Provide manual export instructions
            alert('请使用浏览器截图功能 (Mac: Cmd+Shift+4, Windows: Win+Shift+S) 截取对比结果区域。\n\n或者安装 html2canvas 库以启用自动导出功能。');
            return;
        }

        try {
            const comparisonContainer = document.querySelector('.comparison-container');
            const canvas = await html2canvas(comparisonContainer, {
                backgroundColor: '#ffffff',
                scale: 2,
                logging: false
            });

            // Create download link
            const link = document.createElement('a');
            link.download = `pest_comparison_${Date.now()}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
        } catch (error) {
            console.error('Export error:', error);
            alert('导出失败: ' + error.message);
        }
    }
});
