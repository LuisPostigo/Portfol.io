import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Insights = () => {
  /* ───────── state ───────── */
  const [applicants, setApplicants]   = useState([]);
  const [jobs, setJobs]               = useState([]);
  const [selectedDetails, setSelectedDetails] = useState(null);
  const [selectedId, setSelectedId]   = useState(null);

  /*  pop‑up viewer state  */
  const [docUrl, setDocUrl]           = useState(null);
  const [docOpen, setDocOpen]         = useState(false);

  /* ───────── fetch file status on mount ───────── */
  useEffect(() => {
    axios
      .get('http://localhost:8000/status')
      .then((res) => {
        setApplicants(res.data.filter((f) => f.file_type === 'resume'));
        setJobs(res.data.filter((f) => f.file_type === 'job_posting'));
      })
      .catch((err) => console.error('Failed to fetch file status', err));
  }, []);

  /* ───────── helpers ───────── */
  const formatName = (name) =>
    name
      ? name
          .toLowerCase()
          .split(' ')
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' ')
      : '';

  /* ───────── row selection ───────── */
  const handleSelectFile = (id) => {
    setSelectedId(id);
    axios
      .get(`http://localhost:8000/details?id=${id}`)
      .then((res) => setSelectedDetails(res.data.error ? null : res.data))
      .catch((err) => {
        console.error('Failed to fetch file details', err);
        setSelectedDetails(null);
      });
  };

  /* ───────── view doc in modal ───────── */
  const handleViewDocument = (path) => {
    const relative = path.replace(/\\/g, '/');
    setDocUrl(
      `http://localhost:8000/view?path=${encodeURIComponent(relative)}`
    );
    setDocOpen(true);
  };

  /* ───────── delete file ───────── */
  const handleDelete = (id, path) => {
    if (!window.confirm('Are you sure you want to delete this file?')) return;
    axios
      .delete(
        `http://localhost:8000/delete?id=${id}&path=${encodeURIComponent(path)}`
      )
      .then(() => {
        setApplicants((p) => p.filter((f) => f.id !== id));
        setJobs((p) => p.filter((f) => f.id !== id));
        alert('✅ File deleted!');
      })
      .catch((err) => {
        console.error('Failed to delete', err);
        alert('❌ Failed to delete file');
      });
  };

  /* ───────── table renderer ───────── */
  const renderTable = (files, label) => (
    <div style={{ marginBottom: 30 }}>
      <h3>{label}</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <tbody>
          {files.map((f) => (
            <tr
              key={f.id}
              style={{
                backgroundColor: f.id === selectedId ? '#ede7f6' : '#ffffff',
                transition: 'background-color 0.3s ease',
              }}
            >
              <td
                style={{
                  ...styles.td,
                  cursor: 'pointer',
                  color: '#512da8',
                  width: '60%',
                }}
                onClick={() => handleSelectFile(f.id)}
              >
                {f.original_name || f.file_name}
              </td>
              <td style={{ ...styles.td, width: '40%' }}>
                <button
                  style={styles.viewButton}
                  onClick={() => handleViewDocument(f.file_path)}
                >
                  View
                </button>
                <button
                  style={styles.deleteButton}
                  onClick={() => handleDelete(f.id, f.file_path)}
                >
                  Delete
                </button>
                <button style={styles.matchButton}>Matches</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  /* ───────── modal viewer ───────── */
  const renderDocModal = () =>
    docOpen &&
    docUrl && (
      <div style={styles.overlay}>
        <div style={styles.modal}>
          {/* header strip holds the close button */}
          <div style={styles.header}>
            <button style={styles.closeBtn} onClick={() => setDocOpen(false)}>
              ×
            </button>
          </div>

          {/* document area */}
          <iframe title="document" src={docUrl} style={styles.iframe} />
        </div>
      </div>
    );

  /* ───────── main render ───────── */
  return (
    <>
      {renderDocModal()}

      <div style={{ display: 'flex', padding: 20 }}>
        {/* left column */}
        <div style={{ width: '50%', marginRight: 20 }}>
          {renderTable(jobs, 'Job Postings')}
          {renderTable(applicants, 'Applicants')}
        </div>

        {/* right column */}
        <div style={{ width: '50%' }}>
          <h3>Details</h3>
          {selectedDetails ? (
            <>
              <div style={styles.selectionTag}>
                {selectedId && selectedId.endsWith('a')
                  ? 'Applicant Selected'
                  : 'Job Posting Selected'}
              </div>

              <div style={styles.detailsBox}>
                {selectedDetails.name && (
                  <p>
                    <strong>Name:</strong>{' '}
                    {formatName(selectedDetails.name)}
                  </p>
                )}
                {Object.entries(selectedDetails).map(([k, v]) => {
                  if (k === 'name') return null;
                  const cap = k.charAt(0).toUpperCase() + k.slice(1);
                  return (
                    <p key={k}>
                      <strong>{cap}:</strong> {v}
                    </p>
                  );
                })}
              </div>
            </>
          ) : (
            <p>Select a file to view details.</p>
          )}
        </div>
      </div>
    </>
  );
};

/* ───────── styles ───────── */
const styles = {
  td: {
    padding: 12,
    borderBottom: '1px solid #ddd',
  },
  detailsBox: {
    background: 'rgba(255,255,255,0.6)',
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    borderRadius: 16,
    padding: 30,
    boxShadow: '0 8px 32px rgba(31,38,135,0.2)',
    color: '#333',
    fontSize: 15,
    lineHeight: 1.6,
    marginTop: 20,
  },
  viewButton: {
    marginRight: 6,
    padding: '4px 8px',
    border: '1px solid #4caf50',
    backgroundColor: '#e8f5e9',
    color: '#388e3c',
    borderRadius: 4,
    cursor: 'pointer',
  },
  deleteButton: {
    marginRight: 6,
    padding: '4px 8px',
    border: '1px solid #f44336',
    backgroundColor: '#ffebee',
    color: '#c62828',
    borderRadius: 4,
    cursor: 'pointer',
  },
  matchButton: {
    padding: '4px 8px',
    border: '1px solid #a020f0',
    backgroundColor: '#f9f4fe',
    color: '#a020f0',
    borderRadius: 4,
    cursor: 'pointer',
  },
  selectionTag: {
    backgroundColor: '#a020f0',
    color: '#fff',
    padding: '8px 16px',
    borderRadius: 20,
    fontSize: 14,
    fontWeight: 'bold',
    display: 'inline-block',
    marginBottom: 15,
    textAlign: 'center',
    boxShadow: '0 4px 12px rgba(160,32,240,0.3)',
  },
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.55)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
  },
  modal: {
    position: 'relative',
    width: 'min(900px,95vw)',
    height: '80vh',
    background: '#fff',
    borderRadius: 16,
    boxShadow: '0 20px 40px rgba(0,0,0,0.25)',
    display: 'flex',  
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    height: 46,
    padding: '0 16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    background: '#f5f5f5',
    borderBottom: '1px solid #ddd',
    flexShrink: 0,
  },
  closeBtn: {
    fontSize: 24,
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    lineHeight: 1,
  },
  iframe: {
    flex: 1,
    width: '100%',
    border: 'none',
  },
};

export default Insights;
