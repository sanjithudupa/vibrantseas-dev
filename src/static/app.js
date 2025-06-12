class App extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            batchname: '',
            file: null,
            jobs: [],
            consoleVisible: false,
            activeLog: '',
            activeBatch: '',
            uploading: false
        };
    }

    componentDidMount() {
        this.fetchJobs();
        this.interval = setInterval(this.fetchJobs, 5000);
        const styleTag = document.createElement("style");
        styleTag.innerHTML = styles["@keyframes"];
        document.head.appendChild(styleTag);
    }

    componentWillUnmount() {
        clearInterval(this.interval);
    }

    fetchJobs = () => {
        fetch('/jobs')
            .then(res => res.json())
            .then(data => this.setState({ jobs: data }))
            .catch(err => console.error("Failed to fetch jobs", err));
    }

    fetchLogs = (batchname) => {
        fetch(`/logs/${batchname}`)
            .then(res => res.json())
            .then(data => this.setState({
                consoleVisible: true,
                activeLog: (data.logs || []).join('\n'),
                activeBatch: batchname
            }))
            .catch(err => alert("Failed to fetch logs: " + err.message));
    }

    handleUpload = async (e) => {
        e.preventDefault();

        const { batchname, file } = this.state;
        if (!file || !batchname.trim()) {
            alert("Please select a file and enter a batch name.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);
        formData.append("batchname", batchname);

        this.setState({ uploading: true });

        try {
            const res = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (data.error) throw new Error(data.error);

            await this.fetchJobs();
            this.setState({ batchname: '', file: null });
        } catch (err) {
            alert("Upload failed: " + err.message);
        } finally {
            this.setState({ uploading: false });
        }
    }

    deleteJob = (batchname) => {
        if (!window.confirm(`Are you sure you want to delete job "${batchname}"?`)) return;

        fetch(`/delete/${batchname}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(data => {
                alert(data.message || "Deleted");
                this.fetchJobs();
            })
            .catch(err => alert("Failed to delete job: " + err.message));
    }

    downloadJob = (batchname) => {
        // For now, just hit the same delete endpoint
        fetch(`/delete/${batchname}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(data => {
                alert("Pretending to download... Actually deleted: " + batchname);
                this.fetchJobs();
            })
            .catch(err => alert("Download failed (actually deleted): " + err.message));
    }

    render() {
        return (
            <div className="container" style={{ padding: '20px' }}>
                <h1>VibrantSeas Job Manager</h1>

                {/* Upload Card */}
                <div className="card" style={styles.card}>
                    <h3>Upload New Job</h3>
                    <form onSubmit={this.handleUpload}>
                        <input
                            type="file"
                            accept=".tar.gz"
                            onChange={e => this.setState({ file: e.target.files[0] })}
                        /><br />
                        <input
                            type="text"
                            placeholder="Batch name"
                            value={this.state.batchname}
                            onChange={e => this.setState({ batchname: e.target.value })}
                            required
                            style={{ marginTop: '10px' }}
                        /><br />
                        <button type="submit" style={{ marginTop: '10px' }}>Upload</button>
                        {this.state.uploading && (
                            <div style={styles.spinner}></div>
                        )}
                    </form>
                </div>

                {/* Job Table */}
                <div className="card" style={styles.card}>
                    <h3>Current Jobs</h3>
                    <table border="1" cellPadding="20">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Timestamp</th>
                                <th>Status</th>
                                <th>Console</th>
                                <th>Download</th>
                                <th>Delete</th>
                            </tr>
                        </thead>
                        <tbody>
                            {this.state.jobs.map((job, i) => {
                                const isDone = job.status === 'Done' || job.status.startsWith('Failed') || job.status.startsWith('Error');
                                return (
                                    <tr key={i}>
                                        <td>{job.name}</td>
                                        <td>{job.timestamp}</td>
                                        <td>{job.status}</td>
                                        <td>
                                            <button style={styles.linkButton} onClick={() => this.fetchLogs(job.name)}>
                                                Console
                                            </button>
                                        </td>
                                        <td>
                                            <button
                                                style={isDone ? styles.linkButton : styles.disabledLinkButton}
                                                onClick={() => this.downloadJob(job.name)}
                                                disabled={!isDone}
                                            >
                                                Download
                                            </button>
                                        </td>
                                        <td>
                                            <button
                                                style={isDone ? styles.linkButton : styles.disabledLinkButton}
                                                onClick={() => this.deleteJob(job.name)}
                                                disabled={!isDone}
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>

                {/* Console Popup */}
                {this.state.consoleVisible && (
                    <div style={styles.consoleOverlay}>
                        <div style={styles.consoleCard}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h4>Console Output: {this.state.activeBatch}</h4>
                                <button style={styles.linkButton} onClick={() => this.setState({ consoleVisible: false })}>Close</button>
                            </div>
                            <pre style={styles.logDisplay}>
                                {this.state.activeLog}
                            </pre>
                        </div>
                    </div>
                )}
            </div>
        );
    }
}

const styles = {
    card: {
        padding: '20px',
        marginBottom: '30px',
        border: '1px solid #ccc',
        borderRadius: '10px',
    },
    consoleOverlay: {
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center'
    },
    consoleCard: {
        background: 'white',
        padding: '20px',
        width: '80%',
        maxHeight: '80%',
        overflow: 'auto',
        borderRadius: '10px'
    },
    logDisplay: {
        background: '#eee',
        padding: '10px',
        maxHeight: '60vh',
        overflowY: 'scroll',
        whiteSpace: 'pre-wrap'
    },
    spinner: {
        width: '24px',
        height: '24px',
        border: '3px solid #ccc',
        borderTop: '3px solid #007bff',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
        marginTop: '10px'
    },
    '@keyframes': `
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    `,
    linkButton: {
        background: 'none',
        border: 'none',
        color: 'blue',
        textDecoration: 'underline',
        cursor: 'pointer',
        padding: 0,
        fontSize: 'inherit'
    },
    disabledLinkButton: {
        color: 'gray',
        background: 'none',
        padding: 0,
        border: 'none',
        cursor: 'not-allowed',
        textDecoration: 'none',
        fontSize: 'inherit'
    }
};

ReactDOM.render(<App />, document.getElementById('root'));
