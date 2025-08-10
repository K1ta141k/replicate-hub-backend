class FileManager {
    constructor() {
        this.currentPath = '/';
        this.currentProject = null;
        this.files = [];
        this.folders = [];
        this.currentView = 'grid';
        this.selectedFile = null;
        this.apiBase = 'http://localhost:8000/api';

        // Step 1: grab standard elements
        this.initializeElements();
        // Step 2: dashboard specific elements
        this.elements.projectDashboard = document.getElementById('project-dashboard');
        this.elements.projectsContainer = document.getElementById('projects-container');
        this.elements.newProjectName = document.getElementById('new-project-name');
        this.elements.createProjectBtn = document.getElementById('create-project-btn');
        this.elements.newFileBtn = document.getElementById('new-file-btn');
        this.elements.newFileModal = document.getElementById('new-file-modal');
        this.elements.newFileInput = document.getElementById('new-file-input');
        this.elements.newFileCancel = document.getElementById('new-file-cancel');
        this.elements.newFileConfirm = document.getElementById('new-file-confirm');
        this.elements.runSandboxBtn = document.getElementById('run-sandbox-btn');
        this.elements.chatPane = document.getElementById('chat-pane');
        this.elements.chatToggle = document.getElementById('chat-toggle-btn');
        this.elements.chatClose = document.getElementById('chat-close');
        this.elements.chatMessages = document.getElementById('chat-messages');
        this.elements.chatText = document.getElementById('chat-text');
        this.elements.chatSend = document.getElementById('chat-send');
        this.elements.modelSelect = document.getElementById('model-select');
        // Terminal elements
        this.elements.terminalPane = document.getElementById('terminal-pane');
        this.elements.terminalToggle = document.getElementById('terminal-toggle-btn');
        this.elements.terminalClose = document.getElementById('terminal-close');
        this.elements.terminalOutput = document.getElementById('terminal-output');
        this.elements.terminalCmd = document.getElementById('terminal-cmd');
        this.elements.terminalSend = document.getElementById('terminal-send');
        this.chatHistory = [];
        this.venvName = 'venv';

        // Bind events (needs elements ready)
        this.bindEvents();

        // Skip authentication completely
        this.authenticated = true;

        // Show dashboard immediately
        this.showProjectDashboard();
        
        // Initialize Monaco Editor
        this.initMonacoEditor();
    }

    initMonacoEditor() {
        // Initialize Monaco Editor when the page loads
        if (typeof require !== 'undefined') {
            require.config({ 
                paths: { 
                    'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' 
                } 
            });
            require(['vs/editor/editor.main'], () => {
                this.monaco = window.monaco;
                console.log('Monaco Editor loaded successfully');
                
                // Configure Monaco editor options
                this.monaco.editor.defineTheme('custom-dark', {
                    base: 'vs-dark',
                    inherit: true,
                    rules: [],
                    colors: {
                        'editor.background': '#1e1e1e',
                        'editor.foreground': '#cccccc',
                        'editor.lineHighlightBackground': '#2d2d30',
                        'editor.selectionBackground': '#264f78',
                        'editor.inactiveSelectionBackground': '#3a3d41'
                    }
                });
                
                this.monaco.editor.setTheme('custom-dark');
            });
        } else {
            // Fallback if Monaco fails to load
            console.warn('Monaco Editor failed to load, using fallback textarea');
        }
    }

    createMonacoEditor(filePath, content, fileName) {
        // Destroy existing editor if any
        if (this.currentEditor) {
            this.currentEditor.destroy();
            this.currentEditor = null;
        }

        // Ensure Monaco is loaded
        if (!this.monaco) {
            console.error('Monaco Editor not loaded');
            return;
        }

        // Get the container element
        const container = document.getElementById('monaco-container');
        if (!container) {
            console.error('Monaco container not found');
            return;
        }

        // Clear any existing content
        container.innerHTML = '';

        try {
            // Create new Monaco Editor instance with enhanced features
            this.currentEditor = this.monaco.editor.create(container, {
                value: content || '',
                language: this.getMonacoLanguage(fileName),
                theme: 'custom-dark',
                automaticLayout: true,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                fontSize: 14,
                lineNumbers: 'on',
                roundedSelection: false,
                scrollbar: {
                    vertical: 'visible',
                    horizontal: 'visible'
                },
                wordWrap: 'on',
                folding: true,
                lineDecorationsWidth: 10,
                lineNumbersMinChars: 3,
                renderLineHighlight: 'all',
                selectOnLineNumbers: true,
                glyphMargin: true,
                useTabStops: false,
                fontSize: 14,
                tabSize: 4,
                insertSpaces: true,
                detectIndentation: true,
                trimAutoWhitespace: true,
                largeFileOptimizations: true,
                maxTokenizationLineLength: 20000,
                // Enhanced features
                suggestOnTriggerCharacters: true,
                quickSuggestions: true,
                parameterHints: {
                    enabled: true
                },
                hover: {
                    enabled: true
                },
                contextmenu: true,
                mouseWheelZoom: true,
                smoothScrolling: true,
                cursorBlinking: 'smooth',
                cursorSmoothCaretAnimation: 'on',
                // Code folding
                foldingStrategy: 'indentation',
                showFoldingControls: 'always',
                // Auto-completion
                suggest: {
                    insertMode: 'replace',
                    showKeywords: true,
                    showSnippets: true,
                    showClasses: true,
                    showFunctions: true,
                    showVariables: true,
                    showConstants: true,
                    showEnums: true,
                    showInterfaces: true,
                    showModules: true,
                    showProperties: true,
                    showEvents: true,
                    showOperators: true,
                    showUnits: true,
                    showValues: true,
                    showColors: true,
                    showFiles: true,
                    showReferences: true,
                    showFolders: true,
                    showTypeParameters: true,
                    showWords: true,
                    showColors: true,
                    showUserWords: true
                }
            });

            // Configure language-specific settings
            this.configureLanguageSettings(fileName);

            // Add save button event
            const saveBtn = document.getElementById('ide-save-btn');
            if (saveBtn) {
                // Remove existing event listeners
                const newSaveBtn = saveBtn.cloneNode(true);
                saveBtn.parentNode.replaceChild(newSaveBtn, saveBtn);
                
                newSaveBtn.addEventListener('click', async () => {
                    await this.saveFileContent(filePath, this.currentEditor.getValue());
                });
            }

            // Add keyboard shortcut for save (Ctrl+S)
            this.currentEditor.addCommand(this.monaco.KeyMod.CtrlCmd | this.monaco.KeyCode.KeyS, async () => {
                await this.saveFileContent(filePath, this.currentEditor.getValue());
            });

            // Add keyboard shortcut for find (Ctrl+F)
            this.currentEditor.addCommand(this.monaco.KeyMod.CtrlCmd | this.monaco.KeyCode.KeyF, () => {
                this.currentEditor.trigger('keyboard', 'actions.find', {});
            });

            // Add keyboard shortcut for replace (Ctrl+H)
            this.currentEditor.addCommand(this.monaco.KeyMod.CtrlCmd | this.monaco.KeyCode.KeyH, () => {
                this.currentEditor.trigger('keyboard', 'editor.action.startFindReplaceAction', {});
            });

            // Add keyboard shortcut for go to line (Ctrl+G)
            this.currentEditor.addCommand(this.monaco.KeyMod.CtrlCmd | this.monaco.KeyCode.KeyG, () => {
                this.currentEditor.trigger('keyboard', 'editor.action.gotoLine', {});
            });

            // Track content changes
            this.currentEditor.onDidChangeModelContent(() => {
                this.markFileAsModified(filePath);
            });

            // Focus the editor
            this.currentEditor.focus();

            console.log(`Monaco Editor created for ${fileName} with language: ${this.getMonacoLanguage(fileName)}`);
        } catch (error) {
            console.error('Error creating Monaco Editor:', error);
            // Fallback to textarea
            this.createFallbackEditor(container, content, fileName);
        }
    }

    configureLanguageSettings(fileName) {
        if (!this.currentEditor || !this.monaco) return;

        const language = this.getMonacoLanguage(fileName);
        
        // Configure language-specific settings
        switch (language) {
            case 'python':
                this.monaco.languages.setLanguageConfiguration('python', {
                    comments: {
                        lineComment: '#',
                        blockComment: ['"""', '"""']
                    },
                    brackets: [
                        ['{', '}'],
                        ['[', ']'],
                        ['(', ')']
                    ],
                    autoClosingPairs: [
                        { open: '{', close: '}' },
                        { open: '[', close: ']' },
                        { open: '(', close: ')' },
                        { open: '"', close: '"' },
                        { open: "'", close: "'" }
                    ],
                    surroundingPairs: [
                        { open: '{', close: '}' },
                        { open: '[', close: ']' },
                        { open: '(', close: ')' },
                        { open: '"', close: '"' },
                        { open: "'", close: "'" }
                    ]
                });
                break;
                
            case 'javascript':
            case 'typescript':
                this.monaco.languages.setLanguageConfiguration('javascript', {
                    comments: {
                        lineComment: '//',
                        blockComment: ['/*', '*/']
                    },
                    brackets: [
                        ['{', '}'],
                        ['[', ']'],
                        ['(', ')']
                    ],
                    autoClosingPairs: [
                        { open: '{', close: '}' },
                        { open: '[', close: ']' },
                        { open: '(', close: ')' },
                        { open: '"', close: '"' },
                        { open: "'", close: "'" },
                        { open: '`', close: '`' }
                    ],
                    surroundingPairs: [
                        { open: '{', close: '}' },
                        { open: '[', close: ']' },
                        { open: '(', close: ')' },
                        { open: '"', close: '"' },
                        { open: "'", close: "'" },
                        { open: '`', close: '`' }
                    ]
                });
                break;
                
            case 'html':
                this.monaco.languages.setLanguageConfiguration('html', {
                    comments: {
                        blockComment: ['<!--', '-->']
                    },
                    brackets: [
                        ['{', '}'],
                        ['[', ']'],
                        ['(', ')'],
                        ['<', '>']
                    ],
                    autoClosingPairs: [
                        { open: '{', close: '}' },
                        { open: '[', close: ']' },
                        { open: '(', close: ')' },
                        { open: '"', close: '"' },
                        { open: "'", close: "'" },
                        { open: '<', close: '>' }
                    ],
                    surroundingPairs: [
                        { open: '{', close: '}' },
                        { open: '[', close: ']' },
                        { open: '(', close: ')' },
                        { open: '"', close: '"' },
                        { open: "'", close: "'" },
                        { open: '<', close: '>' }
                    ]
                });
                break;
        }
    }

    createFallbackEditor(container, content, fileName) {
        container.innerHTML = `
            <textarea id="ide-textarea" spellcheck="false" 
                      style="width: 100%; height: calc(100vh - 200px); border: none; outline: none; padding: 10px; 
                             font-family: 'Fira Code', 'Consolas', 'Monaco', monospace; font-size: 14px; 
                             resize: none; background: #1e1e1e; color: #cccccc; line-height: 1.5;">${this.escapeHtml(content || '')}</textarea>
        `;
        
        const textarea = document.getElementById('ide-textarea');
        if (textarea) {
            textarea.focus();
            textarea.setSelectionRange(0, 0);
        }
    }

    getMonacoLanguage(fileName) {
        const ext = fileName.split('.').pop().toLowerCase();
        const languageMap = {
            // JavaScript/TypeScript
            'js': 'javascript',
            'jsx': 'javascript',
            'mjs': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            
            // Python
            'py': 'python',
            'pyw': 'python',
            'pyi': 'python',
            'pyx': 'python',
            'pxd': 'python',
            
            // Web Technologies
            'html': 'html',
            'htm': 'html',
            'xhtml': 'html',
            'css': 'css',
            'scss': 'scss',
            'sass': 'scss',
            'less': 'less',
            'styl': 'stylus',
            
            // Data Formats
            'json': 'json',
            'jsonc': 'jsonc',
            'json5': 'json',
            'xml': 'xml',
            'svg': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'toml': 'toml',
            'ini': 'ini',
            'conf': 'ini',
            'cfg': 'ini',
            
            // Markup
            'md': 'markdown',
            'markdown': 'markdown',
            'rst': 'markdown',
            
            // SQL
            'sql': 'sql',
            'mysql': 'sql',
            'pgsql': 'sql',
            'sqlite': 'sql',
            
            // PHP
            'php': 'php',
            'phtml': 'php',
            'php3': 'php',
            'php4': 'php',
            'php5': 'php',
            'php7': 'php',
            
            // Java
            'java': 'java',
            'class': 'java',
            'jar': 'java',
            
            // C/C++
            'cpp': 'cpp',
            'cc': 'cpp',
            'cxx': 'cpp',
            'c++': 'cpp',
            'c': 'c',
            'h': 'cpp',
            'hpp': 'cpp',
            'hxx': 'cpp',
            
            // C#
            'cs': 'csharp',
            'csx': 'csharp',
            
            // Go
            'go': 'go',
            'mod': 'go',
            'sum': 'go',
            
            // Rust
            'rs': 'rust',
            'rlib': 'rust',
            
            // Ruby
            'rb': 'ruby',
            'erb': 'ruby',
            'rake': 'ruby',
            'gemspec': 'ruby',
            
            // Shell Scripts
            'sh': 'shell',
            'bash': 'shell',
            'zsh': 'shell',
            'fish': 'shell',
            'ksh': 'shell',
            'csh': 'shell',
            'tcsh': 'shell',
            'ps1': 'powershell',
            'psm1': 'powershell',
            'psd1': 'powershell',
            
            // Configuration
            'env': 'properties',
            'properties': 'properties',
            'config': 'properties',
            
            // Documentation
            'txt': 'plaintext',
            'log': 'plaintext',
            'readme': 'plaintext',
            'license': 'plaintext',
            
            // Docker
            'dockerfile': 'dockerfile',
            'docker': 'dockerfile',
            
            // Git
            'gitignore': 'gitignore',
            'gitattributes': 'gitattributes',
            'gitmodules': 'gitmodules',
            
            // Make
            'makefile': 'makefile',
            'mk': 'makefile',
            
            // CMake
            'cmake': 'cmake',
            'cmake.in': 'cmake',
            
            // Lua
            'lua': 'lua',
            
            // Perl
            'pl': 'perl',
            'pm': 'perl',
            't': 'perl',
            
            // R
            'r': 'r',
            'rdata': 'r',
            'rds': 'r',
            
            // Scala
            'scala': 'scala',
            'sc': 'scala',
            
            // Kotlin
            'kt': 'kotlin',
            'kts': 'kotlin',
            
            // Swift
            'swift': 'swift',
            
            // Objective-C
            'm': 'objective-c',
            'mm': 'objective-c',
            'h': 'objective-c'
        };
        
        const language = languageMap[ext];
        if (language) {
            console.log(`Detected language: ${language} for file: ${fileName}`);
            return language;
        }
        
        // Fallback for unknown extensions
        console.log(`No language mapping found for extension: ${ext}, using plaintext`);
        return 'plaintext';
    }

    async saveFileContent(filePath, content) {
        try {
            // Show saving indicator
            const saveBtn = document.getElementById('ide-save-btn');
            if (saveBtn) {
                const originalText = saveBtn.textContent;
                saveBtn.textContent = 'Saving...';
                saveBtn.disabled = true;
                
                // Restore button after save attempt
                setTimeout(() => {
                    saveBtn.textContent = originalText;
                    saveBtn.disabled = false;
                }, 2000);
            }

            const response = await fetch(`${this.apiBase}/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ 
                    path: filePath, 
                    content: content,
                    timestamp: new Date().toISOString()
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.showSuccess(`File saved successfully! ${result.message || ''}`);
                
                // Update the file in the current list if it exists
                this.updateFileInList(filePath, content);
                
                // Add a visual indicator that the file was saved
                this.markFileAsSaved(filePath);
                
                return true;
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Save failed:', error);
            const errorMessage = error.message || 'Failed to save file';
            this.showError(`Save failed: ${errorMessage}`);
            
            // Show retry option
            this.showRetrySaveDialog(filePath, content);
            
            return false;
        }
    }

    updateFileInList(filePath, content) {
        // Find the file in the current files list and update its size
        const fileName = filePath.split('/').pop();
        const fileIndex = this.files.findIndex(f => f.name === fileName);
        if (fileIndex !== -1) {
            // Update the file size (rough estimation)
            const sizeInBytes = new Blob([content]).size;
            this.files[fileIndex].size = this.formatFileSize(sizeInBytes);
            
            // Re-render files to show updated size
            this.renderFiles();
        }
    }

    markFileAsSaved(filePath) {
        // Remove modified indicator and add saved indicator
        const tab = document.querySelector(`.ide-tab[data-path="${filePath}"]`);
        if (tab) {
            tab.classList.remove('modified');
            tab.classList.add('recently-saved');
            tab.removeAttribute('title');
            
            setTimeout(() => {
                tab.classList.remove('recently-saved');
            }, 3000);
        }
    }

    markFileAsModified(filePath) {
        // Add visual indicator that file has unsaved changes
        const tab = document.querySelector(`.ide-tab[data-path="${filePath}"]`);
        if (tab && !tab.classList.contains('modified')) {
            tab.classList.add('modified');
            tab.setAttribute('title', 'File has unsaved changes');
        }
    }

    showRetrySaveDialog(filePath, content) {
        const retryDialog = document.createElement('div');
        retryDialog.className = 'retry-save-dialog';
        retryDialog.innerHTML = `
            <div class="retry-save-content">
                <h4>Save Failed</h4>
                <p>The file could not be saved. Would you like to retry?</p>
                <div class="retry-buttons">
                    <button class="retry-btn">Retry Save</button>
                    <button class="cancel-retry-btn">Cancel</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(retryDialog);
        
        // Add event listeners
        retryDialog.querySelector('.retry-btn').addEventListener('click', async () => {
            retryDialog.remove();
            await this.saveFileContent(filePath, content);
        });
        
        retryDialog.querySelector('.cancel-retry-btn').addEventListener('click', () => {
            retryDialog.remove();
        });
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (retryDialog.parentNode) {
                retryDialog.remove();
            }
        }, 10000);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    initializeElements() {
        this.elements = {
            loginOverlay: document.getElementById('login-overlay'),
            mainContainer: document.getElementById('main-container'),
            pinInput: document.getElementById('pin-input'),
            loginBtn: document.getElementById('login-btn'),
            loginError: document.getElementById('login-error'),
            logoutBtn: document.getElementById('logout-btn'),
            filesContainer: document.getElementById('files-container'),
            breadcrumb: document.getElementById('breadcrumb'),
            folderTree: document.getElementById('folder-tree'),
            fileUpload: document.getElementById('file-upload'),
            uploadProgress: document.getElementById('upload-progress'),
            progressFill: document.getElementById('progress-fill'),
            progressText: document.getElementById('progress-text'),
            searchInput: document.getElementById('search-input'),
            contextMenu: document.getElementById('context-menu'),
            renameModal: document.getElementById('rename-modal'),
            renameInput: document.getElementById('rename-input'),
            renameCancel: document.getElementById('rename-cancel'),
            renameConfirm: document.getElementById('rename-confirm'),
            loading: document.getElementById('loading'),
            idePane: document.getElementById('ide-pane'),
            ideResizer: document.getElementById('ide-resizer'),
            ideCloseBtn: document.getElementById('ide-close-btn'),
            ideTabs: document.getElementById('ide-tabs'),
            ideContent: document.getElementById('ide-content')
        };
    }

    bindEvents() {
        // Authentication events
        this.elements.loginBtn.addEventListener('click', () => this.handleLogin());
        this.elements.pinInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleLogin();
        });
        this.elements.logoutBtn.addEventListener('click', () => this.handleLogout());
        
        // File upload
        this.elements.fileUpload.addEventListener('change', (e) => this.handleFileUpload(e));
        
        // Search
        this.elements.searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
        
        // View controls
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchView(e.target.dataset.view));
        });
        
        // Context menu
        document.addEventListener('click', () => this.hideContextMenu());
        this.elements.contextMenu.addEventListener('click', (e) => this.handleContextMenu(e));
        
        // Rename modal
        this.elements.renameCancel.addEventListener('click', () => this.hideRenameModal());
        this.elements.renameConfirm.addEventListener('click', () => this.confirmRename());
        this.elements.renameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.confirmRename();
        });

        // New file modal
        if (this.elements.newFileBtn) {
            this.elements.newFileBtn.addEventListener('click', () => this.showNewFileModal());
        }
        if (this.elements.newFileCancel) {
            this.elements.newFileCancel.addEventListener('click', () => this.hideNewFileModal());
        }
        if (this.elements.newFileConfirm) {
            this.elements.newFileConfirm.addEventListener('click', () => this.createNewFile());
        }
        
        // Prevent context menu on right click
        document.getElementById('main-container').addEventListener('contextmenu', (e) => e.preventDefault());

        // IDE resizer events
        this.elements.ideResizer.addEventListener('mousedown', this.startResizing.bind(this));
        document.addEventListener('mousemove', this.handleResizing.bind(this));
        document.addEventListener('mouseup', this.stopResizing.bind(this));

        // IDE close button event
        this.elements.ideCloseBtn.addEventListener('click', this.closeIdePane.bind(this));

        // IDE drop area events
        this.elements.idePane.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            this.elements.idePane.classList.add('dragover');
        });

        this.elements.idePane.addEventListener('dragleave', (e) => {
            if (!this.elements.idePane.contains(e.relatedTarget)) {
                this.elements.idePane.classList.remove('dragover');
            }
        });

        this.elements.idePane.addEventListener('drop', (e) => {
            e.preventDefault();
            this.elements.idePane.classList.remove('dragover');
            
            try {
                const fileData = JSON.parse(e.dataTransfer.getData('text/plain'));
                const fileItem = this.elements.filesContainer.querySelector(`[data-path="${fileData.path}"]`);
                if (fileItem) {
                    this.openFileTab(fileItem);
                }
            } catch (error) {
                console.error('Error parsing dropped file data:', error);
            }
        });

        // Project creation
        if (this.elements.createProjectBtn) {
            this.elements.createProjectBtn.addEventListener('click', () => this.createProject());
        }

        // Selecting a project (event delegation)
        if (this.elements.projectsContainer) {
            this.elements.projectsContainer.addEventListener('click', (e) => {
                const card = e.target.closest('.project-card');
                if (card) {
                    this.openProject(card.dataset.name);
                }
            });
        }

        // Run sandbox
        if (this.elements.runSandboxBtn) {
            this.elements.runSandboxBtn.addEventListener('click', () => this.runSandbox());
        }

        // Chat events
        if (this.elements.chatToggle) {
            this.elements.chatToggle.addEventListener('click', () => this.elements.chatPane.style.display = 'block');
        }
        if (this.elements.chatClose) {
            this.elements.chatClose.addEventListener('click', () => this.elements.chatPane.style.display = 'none');
        }
        if (this.elements.chatSend) {
            this.elements.chatSend.addEventListener('click', () => this.sendChat());
        }
        if (this.elements.chatText) {
            this.elements.chatText.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendChat();
                }
            });
        }

        // Terminal events
        if (this.elements.terminalToggle) {
            this.elements.terminalToggle.addEventListener('click', () => {
                this.elements.terminalPane.style.display = 'block';
                this.elements.terminalCmd.focus();
            });
        }
        if (this.elements.terminalClose) {
            this.elements.terminalClose.addEventListener('click', () => this.elements.terminalPane.style.display = 'none');
        }
        if (this.elements.terminalSend) {
            this.elements.terminalSend.addEventListener('click', () => this.sendTerminalCmd());
        }
        if (this.elements.terminalCmd) {
            this.elements.terminalCmd.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.sendTerminalCmd();
                }
            });
        }
    }

    async checkAuthentication() {
        try {
            const response = await fetch(`${this.apiBase}/check-auth`, {
                credentials: 'include'
            });
            const data = await response.json();
            this.authenticated = data.authenticated;
            
            if (this.authenticated) {
                this.showMainInterface();
                this.loadCurrentDirectory();
            } else {
                this.showLoginInterface();
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.showLoginInterface();
        }
    }

    async handleLogin() {
        const pin = this.elements.pinInput.value.trim();
        if (!pin) {
            this.showLoginError('Please enter a PIN');
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ pin })
            });

            if (response.ok) {
                this.authenticated = true;
                this.hideLoginError();
                this.showMainInterface();
                this.loadCurrentDirectory();
            } else {
                const data = await response.json();
                this.showLoginError(data.error || 'Invalid PIN');
            }
        } catch (error) {
            console.error('Login failed:', error);
            this.showLoginError('Login failed. Please try again.');
        }
    }

    async handleLogout() {
        try {
            await fetch(`${this.apiBase}/logout`, {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout failed:', error);
        }
        
        this.authenticated = false;
        this.showLoginInterface();
    }

    showLoginInterface() {
        this.elements.loginOverlay.style.display = 'flex';
        this.elements.mainContainer.style.display = 'none';
        this.elements.pinInput.value = '';
        this.elements.pinInput.focus();
    }

    showMainInterface() {
        this.elements.loginOverlay.style.display = 'none';
        this.elements.mainContainer.style.display = 'block';
    }

    showLoginError(message) {
        this.elements.loginError.querySelector('span').textContent = message;
        this.elements.loginError.style.display = 'flex';
    }

    hideLoginError() {
        this.elements.loginError.style.display = 'none';
    }

    async loadCurrentDirectory() {
        if (!this.authenticated) return;
        
        this.showLoading();
        try {
            const response = await fetch(`${this.apiBase}/list?path=${encodeURIComponent(this.currentPath)}`, {
                credentials: 'include'
            });
            if (!response.ok) throw new Error('Failed to load directory');
            const data = await response.json();
            this.files = data.files || [];
            this.folders = data.folders || [];
            this.updateBreadcrumb();
            this.updateFolderTree();
            this.renderFiles();
        } catch (error) {
            console.error('Error loading directory:', error);
            this.showError('Failed to load directory contents');
        } finally {
            this.hideLoading();
        }
    }

    updateBreadcrumb() {
        const pathParts = this.currentPath.split('/').filter(part => part);
        let html = '<span class="breadcrumb-item active" data-path="/">Home</span>';
        let currentPath = '';
        pathParts.forEach(part => {
            currentPath += '/' + part;
            html += `<span class="breadcrumb-item" data-path="${currentPath}">${part}</span>`;
        });
        this.elements.breadcrumb.innerHTML = html;
        this.elements.breadcrumb.querySelectorAll('.breadcrumb-item').forEach(item => {
            item.addEventListener('click', () => {
                this.navigateToPath(item.dataset.path);
            });
        });
    }

    updateFolderTree() {
        // List only folders in the sidebar
        let treeHtml = `<div class="folder-item root-folder" data-path="/">
            <i class="fas fa-home"></i>
            <span>Home</span>
        </div>`;
        this.folders.forEach(folder => {
            treeHtml += `<div class="folder-item" data-path="${folder.path}">
                <i class="fas fa-folder"></i>
                <span>${folder.name}</span>
            </div>`;
        });
        this.elements.folderTree.innerHTML = treeHtml;
        this.elements.folderTree.querySelectorAll('.folder-item').forEach(item => {
            item.addEventListener('click', () => {
                this.navigateToPath(item.dataset.path);
            });
        });
    }

    renderFiles() {
        // Hide dotfiles
        const allItems = [...this.folders, ...this.files].filter(item => !item.name.startsWith('.'));
        if (allItems.length === 0) {
            this.elements.filesContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <p>This folder is empty</p>
                </div>
            `;
            return;
        }
        const gridHtml = this.renderGridView(allItems);
        const listHtml = this.renderListView(allItems);
        this.elements.filesContainer.innerHTML = `
            <div class="files-grid ${this.currentView === 'grid' ? 'active' : ''}">${gridHtml}</div>
            <div class="files-list ${this.currentView === 'list' ? 'active' : ''}">${listHtml}</div>
        `;
        this.addFileItemListeners();
    }

    renderGridView(items) {
        return items.map(item => {
            const isFolder = 'path' in item;
            const icon = isFolder ? 'fa-folder' : this.getFileIcon(item.type);
            const size = isFolder ? '' : `<div class="file-size">${item.size}</div>`;
            return `
                <div class="file-item ${isFolder ? 'folder' : 'file'}" 
                     data-name="${item.name}" 
                     data-type="${item.type || ''}"
                     data-path="${isFolder ? item.path : this.currentPath + '/' + item.name}">
                    <i class="fas ${icon}"></i>
                    <div class="file-name">${item.name}</div>
                    ${size}
                </div>
            `;
        }).join('');
    }

    renderListView(items) {
        return items.map(item => {
            const isFolder = 'path' in item;
            const icon = isFolder ? 'fa-folder' : this.getFileIcon(item.type);
            const size = isFolder ? '' : `<div class="file-size">${item.size}</div>`;
            return `
                <div class="file-item ${isFolder ? 'folder' : 'file'}" 
                     data-name="${item.name}" 
                     data-type="${item.type || ''}"
                     data-path="${isFolder ? item.path : this.currentPath + '/' + item.name}">
                    <i class="fas ${icon}"></i>
                    <div class="file-name">${item.name}</div>
                    ${size}
                </div>
            `;
        }).join('');
    }

    getFileIcon(type) {
        const iconMap = {
            'image': 'fa-image',
            'document': 'fa-file-alt',
            'video': 'fa-video',
            'audio': 'fa-music',
            'archive': 'fa-archive',
            'default': 'fa-file'
        };
        return iconMap[type] || iconMap.default;
    }

    addFileItemListeners() {
        // File item click events
        this.elements.filesContainer.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.closest('.context-menu')) return;
                this.selectFile(item);
            });
            
            item.addEventListener('dblclick', (e) => {
                if (e.target.closest('.context-menu')) return;
                if (item.classList.contains('folder')) {
                    this.navigateToPath(item.dataset.path);
                } else {
                    this.openFileTab(item);
                }
            });

            // Drag and drop functionality
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', JSON.stringify({
                    name: item.dataset.name,
                    path: item.dataset.path,
                    type: item.dataset.type
                }));
                e.dataTransfer.effectAllowed = 'copy';
            });

            item.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                this.showContextMenu(e, item);
            });
        });

        // IDE drop area events
        this.elements.idePane.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            this.elements.idePane.classList.add('dragover');
        });

        this.elements.idePane.addEventListener('dragleave', (e) => {
            if (!this.elements.idePane.contains(e.relatedTarget)) {
                this.elements.idePane.classList.remove('dragover');
            }
        });

        this.elements.idePane.addEventListener('drop', (e) => {
            e.preventDefault();
            this.elements.idePane.classList.remove('dragover');
            
            try {
                const fileData = JSON.parse(e.dataTransfer.getData('text/plain'));
                const fileItem = this.elements.filesContainer.querySelector(`[data-path="${fileData.path}"]`);
                if (fileItem) {
                    this.openFileTab(fileItem);
                }
            } catch (error) {
                console.error('Error parsing dropped file data:', error);
            }
        });
    }

    selectFile(item) {
        this.elements.filesContainer.querySelectorAll('.file-item').forEach(el => {
            el.classList.remove('selected');
        });
        item.classList.add('selected');
        this.selectedFile = item;
    }

    navigateToPath(path) {
        this.currentPath = path;
        this.loadCurrentDirectory();
        this.elements.folderTree.querySelectorAll('.folder-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.path === path) {
                item.classList.add('active');
            }
        });
    }

    async handleFileUpload(event) {
        if (!this.authenticated) return;
        
        const files = Array.from(event.target.files);
        if (files.length === 0) return;
        this.showUploadProgress();
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const progress = ((i + 1) / files.length) * 100;
            try {
                await this.uploadFile(file);
                this.updateProgress(progress);
            } catch (error) {
                console.error('Upload failed:', error);
                this.showError(`Failed to upload ${file.name}`);
            }
        }
        this.hideUploadProgress();
        this.loadCurrentDirectory();
        event.target.value = '';
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('path', this.currentPath);
        const response = await fetch(`${this.apiBase}/upload`, {
            method: 'POST',
            credentials: 'include',
            body: formData
        });
        if (!response.ok) throw new Error('Upload failed');
    }

    downloadFile(filePath) {
        // Use backend download endpoint
        const url = `${this.apiBase}/download?path=${encodeURIComponent(filePath)}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = filePath.split('/').pop();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    handleSearch(query) {
        const items = this.elements.filesContainer.querySelectorAll('.file-item');
        items.forEach(item => {
            const fileName = item.dataset.name.toLowerCase();
            const matches = fileName.includes(query.toLowerCase());
            item.style.display = matches ? 'block' : 'none';
        });
    }

    switchView(view) {
        this.currentView = view;
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
        const gridView = this.elements.filesContainer.querySelector('.files-grid');
        const listView = this.elements.filesContainer.querySelector('.files-list');
        if (view === 'grid') {
            gridView.classList.add('active');
            listView.classList.remove('active');
        } else {
            gridView.classList.remove('active');
            listView.classList.add('active');
        }
    }

    showContextMenu(event, fileItem) {
        this.selectedFile = fileItem;
        const menu = this.elements.contextMenu;
        menu.style.display = 'block';
        menu.style.left = event.pageX + 'px';
        menu.style.top = event.pageY + 'px';
        const rect = menu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            menu.style.left = (event.pageX - rect.width) + 'px';
        }
        if (rect.bottom > window.innerHeight) {
            menu.style.top = (event.pageY - rect.height) + 'px';
        }
    }

    hideContextMenu() {
        this.elements.contextMenu.style.display = 'none';
    }

    async handleContextMenu(event) {
        const action = event.target.closest('.context-item')?.dataset.action;
        if (!action) return;
        this.hideContextMenu();
        switch (action) {
            case 'download':
                if (this.selectedFile && !this.selectedFile.classList.contains('folder')) {
                    this.downloadFile(this.selectedFile.dataset.path);
                }
                break;
            case 'rename':
                this.showRenameModal();
                break;
            case 'delete':
                this.deleteFile();
                break;
        }
    }

    showRenameModal() {
        if (!this.selectedFile) return;
        const currentName = this.selectedFile.dataset.name;
        this.elements.renameInput.value = currentName;
        this.elements.renameInput.select();
        this.elements.renameModal.style.display = 'flex';
        this.elements.renameInput.focus();
    }

    hideRenameModal() {
        this.elements.renameModal.style.display = 'none';
    }

    // ---------- New File Modal ---------- //
    showNewFileModal() {
        this.elements.newFileInput.value = '';
        this.elements.newFileModal.style.display = 'flex';
        this.elements.newFileInput.focus();
    }

    hideNewFileModal() {
        this.elements.newFileModal.style.display = 'none';
    }

    async createNewFile() {
        const fileName = this.elements.newFileInput.value.trim();
        if (!fileName) return;
        try {
            const relPath = (this.currentPath === '/' ? '' : this.currentPath) + '/' + fileName;
            const resp = await fetch(`${this.apiBase}/create-file`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ path: relPath, content: '' })
            });
            if (!resp.ok) {
                const d = await resp.json().catch(() => ({}));
                alert(d.detail || 'Failed to create file');
                return;
            }
            this.hideNewFileModal();
            this.loadCurrentDirectory();
        } catch (err) {
            console.error('Create file error:', err);
        }
    }

    async confirmRename() {
        if (!this.selectedFile) return;
        const newName = this.elements.renameInput.value.trim();
        if (!newName) return;
        try {
            await fetch(`${this.apiBase}/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ path: this.selectedFile.dataset.path, newName })
            });
            this.hideRenameModal();
            this.loadCurrentDirectory();
        } catch (error) {
            console.error('Rename failed:', error);
            this.showError('Failed to rename file');
        }
    }

    async deleteFile() {
        if (!this.selectedFile) return;
        if (!confirm(`Are you sure you want to delete "${this.selectedFile.dataset.name}"?`)) {
            return;
        }
        try {
            await fetch(`${this.apiBase}/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ path: this.selectedFile.dataset.path })
            });
            this.loadCurrentDirectory();
        } catch (error) {
            console.error('Delete failed:', error);
            this.showError('Failed to delete file');
        }
    }

    showUploadProgress() {
        this.elements.uploadProgress.style.display = 'flex';
        this.updateProgress(0);
    }

    hideUploadProgress() {
        this.elements.uploadProgress.style.display = 'none';
    }

    updateProgress(percentage) {
        this.elements.progressFill.style.width = percentage + '%';
        this.elements.progressText.textContent = Math.round(percentage) + '%';
    }

    showLoading() {
        this.elements.loading.style.display = 'flex';
    }

    hideLoading() {
        this.elements.loading.style.display = 'none';
    }

    showError(message) {
        alert(message);
    }

    showSuccess(message) {
        // Simple success feedback; replace with nicer toast if desired
        console.log(message);
        alert(message);
    }

    // Tabbed preview modal logic
    openTabs = [];
    openFileTab(item) {
        // Show IDE pane when opening a file
        this.elements.idePane.classList.add('visible');
        
        const filePath = item.dataset.path;
        const fileName = item.dataset.name;
        const fileType = item.dataset.type;
        
        // If already open, focus tab
        if (this.openTabs.some(tab => tab.path === filePath)) {
            this.focusTab(filePath);
            return;
        }
        
        // Add new tab
        this.openTabs.push({ path: filePath, name: fileName, type: fileType });
        this.renderIdeTabs();
        this.focusTab(filePath);
    }

    focusTab(filePath) {
        this.activeTab = filePath;
        this.renderIdeTabs();
        this.renderIdeContent();
    }

    closeTab(filePath) {
        // Check if file has unsaved changes
        if (this.hasUnsavedChanges(filePath)) {
            this.showUnsavedChangesDialog(filePath);
            return;
        }
        
        this.openTabs = this.openTabs.filter(tab => tab.path !== filePath);
        if (this.activeTab === filePath && this.openTabs.length > 0) {
            this.activeTab = this.openTabs[this.openTabs.length - 1].path;
        } else if (this.openTabs.length === 0) {
            this.closeIdePane();
            return;
        }
        
        // Clean up Monaco Editor if closing the active tab
        if (this.activeTab === filePath && this.currentEditor) {
            this.currentEditor.destroy();
            this.currentEditor = null;
        }
        
        this.renderIdeTabs();
        this.renderIdeContent();
    }

    hasUnsavedChanges(filePath) {
        const tab = document.querySelector(`.ide-tab[data-path="${filePath}"]`);
        return tab && tab.classList.contains('modified');
    }

    showUnsavedChangesDialog(filePath) {
        const dialog = document.createElement('div');
        dialog.className = 'unsaved-changes-dialog';
        dialog.innerHTML = `
            <div class="unsaved-changes-content">
                <h4>Unsaved Changes</h4>
                <p>The file "${filePath.split('/').pop()}" has unsaved changes. What would you like to do?</p>
                <div class="unsaved-buttons">
                    <button class="save-close-btn">Save & Close</button>
                    <button class="close-without-save-btn">Close Without Saving</button>
                    <button class="cancel-close-btn">Cancel</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        // Add event listeners
        dialog.querySelector('.save-close-btn').addEventListener('click', async () => {
            if (this.currentEditor && this.activeTab === filePath) {
                await this.saveFileContent(filePath, this.currentEditor.getValue());
            }
            dialog.remove();
            this.closeTab(filePath);
        });
        
        dialog.querySelector('.close-without-save-btn').addEventListener('click', () => {
            dialog.remove();
            this.closeTab(filePath);
        });
        
        dialog.querySelector('.cancel-close-btn').addEventListener('click', () => {
            dialog.remove();
        });
    }

    renderIdeTabs() {
        if (!this.openTabs.length) {
            this.elements.ideTabs.innerHTML = '';
            return;
        }

        let tabsHtml = '';
        for (const tab of this.openTabs) {
            tabsHtml += `<div class="ide-tab${tab.path === this.activeTab ? ' active' : ''}" data-path="${tab.path}">
                <span>${tab.name}</span>
                <button class="close-tab-btn" data-path="${tab.path}">&times;</button>
            </div>`;
        }
        this.elements.ideTabs.innerHTML = tabsHtml;

        // Tab switching
        this.elements.ideTabs.querySelectorAll('.ide-tab').forEach(tabEl => {
            tabEl.addEventListener('click', () => this.focusTab(tabEl.dataset.path));
        });

        // Tab closing
        this.elements.ideTabs.querySelectorAll('.close-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.closeTab(btn.dataset.path);
            });
        });
    }

    async renderIdeContent() {
        if (!this.activeTab || !this.openTabs.length) {
            this.elements.ideContent.innerHTML = '';
            return;
        }

        const tab = this.openTabs.find(t => t.path === this.activeTab);
        if (!tab) return;

        const fileType = tab.type;
        const filePath = tab.path;
        const fileName = tab.name;

        // Check file size before proceeding
        const fileObj = this.files.find(f => f.name === fileName);
        const MAX_PREVIEW_SIZE = 1024 * 1024; // 1MB
        const MAX_VIDEO_SIZE = 100 * 1024 * 1024; // 100MB

        if (fileObj) {
            const fileSize = this.parseSize(fileObj.size);
            
            if (fileType === 'video' && fileSize > MAX_VIDEO_SIZE) {
                this.elements.ideContent.innerHTML = `
                    <div style="padding: 20px; color: #dc3545;">
                        Video file too large to preview (over 100MB).
                    </div>`;
                return;
            }
            
            if (fileType !== 'video' && fileType !== 'image' && fileSize > MAX_PREVIEW_SIZE) {
                this.elements.ideContent.innerHTML = `
                    <div style="padding: 20px; color: #dc3545;">
                        File too large to preview (over 1MB).
                    </div>`;
                return;
            }
        }

        if (fileType === 'image') {
            this.elements.ideContent.innerHTML = `
                <img style="max-width: 100%; height: auto;" 
                     src="${this.apiBase}/download?path=${encodeURIComponent(filePath)}" 
                     alt="${fileName}">`;
        } else if (fileType === 'video') {
            this.elements.ideContent.innerHTML = `
                <video style="max-width: 100%; height: auto;" controls preload="metadata">
                    <source src="${this.apiBase}/download?path=${encodeURIComponent(filePath)}" type="video/mp4">
                    <source src="${this.apiBase}/download?path=${encodeURIComponent(filePath)}" type="video/webm">
                    <source src="${this.apiBase}/download?path=${encodeURIComponent(filePath)}" type="video/ogg">
                    Your browser does not support the video tag.
                </video>`;
        } else if (fileType === 'audio') {
            this.elements.ideContent.innerHTML = `
                <audio style="width: 100%;" controls preload="metadata">
                    <source src="${this.apiBase}/download?path=${encodeURIComponent(filePath)}">
                    Your browser does not support the audio element.
                </audio>`;
        } else if (fileType === 'document' || fileType === 'default') {
            try {
                const resp = await fetch(`${this.apiBase}/read?path=${encodeURIComponent(filePath)}`, {
                    credentials: 'include'
                });
                if (!resp.ok) throw new Error('Failed to load file content');
                const data = await resp.json();
                const content = data.content ?? '';

                // Insert a container for Monaco Editor
                this.elements.ideContent.innerHTML = '<div id="monaco-container" style="width:100%;height:100%;"></div>';
                this.createMonacoEditor(filePath, content, fileName);
            } catch (error) {
                console.error('Failed to load file:', error);
                this.elements.ideContent.innerHTML = '<div style="padding:20px;color:#dc3545;">Failed to load file.</div>';
            }
        }
    }

    // ---------- IDE Pane Utilities ---------- //
    startResizing(e) {
        this.isResizing = true;
        this.startX = e.clientX;
        this.startWidth = this.elements.idePane.offsetWidth;
        e.preventDefault();
    }

    handleResizing(e) {
        if (!this.isResizing) return;
        const dx = this.startX - e.clientX;
        const newWidth = this.startWidth + dx;
        const minWidth = 200;
        const maxWidth = window.innerWidth - 200;
        this.elements.idePane.style.width = Math.min(maxWidth, Math.max(minWidth, newWidth)) + 'px';
    }

    stopResizing() {
        this.isResizing = false;
    }

    closeIdePane() {
        this.elements.idePane.classList.remove('visible');
        if (this.currentEditor) {
            this.currentEditor.destroy();
            this.currentEditor = null;
        }
        this.openTabs = [];
        this.activeTab = null;
        this.renderIdeTabs();
        this.elements.ideContent.innerHTML = '';
    }

    // Convert human-readable size (e.g. "1.2 MB") to bytes
    parseSize(sizeStr) {
        if (!sizeStr) return 0;
        const parts = sizeStr.trim().split(/\s+/);
        const value = parseFloat(parts[0]);
        if (isNaN(value)) return 0;
        const unit = (parts[1] || 'B').toUpperCase();
        const multipliers = { 'B': 1, 'K': 1024, 'KB': 1024, 'M': 1024 ** 2, 'MB': 1024 ** 2, 'G': 1024 ** 3, 'GB': 1024 ** 3 };
        return value * (multipliers[unit] || 1);
    }

    // ---------- Dashboard stub ---------- //
    async loadProjects() {
        try {
            const resp = await fetch(`${this.apiBase}/projects`, { credentials: 'include' });
            if (!resp.ok) throw new Error('Failed to fetch projects');
            const data = await resp.json();
            this.renderProjects(data.projects || []);
        } catch (err) {
            console.error('Error loading projects:', err);
            this.renderProjects([]);
        }
    }

    renderProjects(projects) {
        if (!this.elements.projectsContainer) return;
        if (projects.length === 0) {
            this.elements.projectsContainer.innerHTML = '<p style="padding:10px;color:#999;">No projects yet.</p>';
            return;
        }
        this.elements.projectsContainer.innerHTML = projects.map(name => `
            <div class="project-card" data-name="${name}">
                <i class="fas fa-folder-open"></i>
                <span>${name}</span>
            </div>
        `).join('');
    }

    async createProject() {
        const name = (this.elements.newProjectName.value || '').trim();
        if (!name) return;
        try {
            const resp = await fetch(`${this.apiBase}/projects`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ name })
            });
            if (!resp.ok) {
                const d = await resp.json().catch(() => ({}));
                alert(d.detail || 'Failed to create project');
                return;
            }
            this.elements.newProjectName.value = '';
            this.loadProjects();
        } catch (err) {
            console.error('Create project failed:', err);
        }
    }

    openProject(projectName) {
        this.currentProject = projectName;
        this.currentPath = '/';
        this.elements.projectDashboard.style.display = 'none';
        this.showMainInterface();
        // Initialise sandbox workspace for this project
        this.initSandbox(projectName).catch(err => console.error('Sandbox init failed', err));
        this.loadCurrentDirectory();
    }

    async initSandbox(projectName) {
        try {
            await fetch(`${this.apiBase}/sandbox/init`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ project: projectName })
            });
        } catch (err) {
            console.error('Sandbox init error', err);
        }
    }

    async runSandbox() {
        const projectName = (this.currentPath.split('/').filter(Boolean)[0]) || '';
        if (!projectName) {
            this.showError('No project selected to run.');
            return;
        }
        try {
            const resp = await fetch(`${this.apiBase}/sandbox/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ project: projectName })
            });
            if (!resp.ok) throw new Error(await resp.text());
            window.open('http://localhost:5173', '_blank');
        } catch (err) {
            console.error('Sandbox start failed:', err);
            this.showError('Failed to start sandbox');
        }
    }

    showProjectDashboard() {
        if (!this.elements.projectDashboard) return;
        this.elements.projectDashboard.style.display = 'block';
        this.elements.mainContainer.style.display = 'none';
        this.loadProjects();
    }

    appendChat(role, content) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-msg ${role}`;
        msgDiv.textContent = content;
        this.elements.chatMessages.appendChild(msgDiv);
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
        this.chatHistory.push({ role, content });
    }

    async sendChat() {
        const text = this.elements.chatText.value.trim();
        if (!text) return;
        this.elements.chatText.value = '';
        this.appendChat('user', text);
        const projectName = (this.currentPath.split('/').filter(Boolean)[0]) || 'scratch';
        const payload = {
            project: projectName,
            model: this.elements.modelSelect.value,
            messages: this.chatHistory
        };
        try {
            const resp = await fetch(`${this.apiBase}/ai/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(payload)
            });
            if (!resp.ok) throw new Error(await resp.text());
            const data = await resp.json();
            this.appendChat('assistant', data.assistant || '(no response)');
        } catch (err) {
            console.error('chat error', err);
            this.appendChat('assistant', 'Error: ' + err.message);
        }
    }

    appendTerminal(text, cls = '') {
        const span = document.createElement('span');
        span.textContent = text + '\n';
        if (cls) span.className = cls;
        this.elements.terminalOutput.appendChild(span);
        this.elements.terminalOutput.scrollTop = this.elements.terminalOutput.scrollHeight;
    }

    async sendTerminalCmd() {
        const cmd = (this.elements.terminalCmd.value || '').trim();
        if (!cmd) return;
        this.elements.terminalCmd.value = '';
        const prompt = `(${this.venvName})user@${this.currentProject || 'sandbox'}$`;
        this.appendTerminal(`${prompt} ${cmd}`, 'user-cmd');
        try {
            const resp = await fetch(`${this.apiBase}/sandbox/exec`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ cmd })
            });
            const data = await resp.json();
            if (data.stdout) this.appendTerminal(data.stdout, 'stdout');
            if (data.stderr) this.appendTerminal(data.stderr, 'stderr');
            if (data.error) this.appendTerminal(data.error, 'stderr');
            // refocus
            this.elements.terminalCmd.focus();
        } catch (err) {
            this.appendTerminal('Error: ' + err.message, 'stderr');
            this.elements.terminalCmd.focus();
        }
    }
}

// Instantiate the FileManager once the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    new FileManager();
});