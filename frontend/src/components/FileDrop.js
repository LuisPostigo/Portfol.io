import React from 'react';
import { useDropzone } from 'react-dropzone';

const FileDrop = ({ label, onFilesSelected }) => {
  const { getRootProps, getInputProps, acceptedFiles } = useDropzone({
    onDrop: onFilesSelected,
    accept: { 'application/pdf': ['.pdf'], 'text/plain': ['.txt'] },
    multiple: true
  });

  const isEmpty = acceptedFiles.length === 0;

  return (
    <div {...getRootProps()} style={styles.dropArea}>
      <input {...getInputProps()} />
      <div style={{
        ...styles.content,
        justifyContent: isEmpty ? 'center' : 'flex-start'  // ✨ Dynamically change centering
      }}>
        {isEmpty ? (
          <>
            <p style={{ marginBottom: '4px' }}>{label}</p>
            <p style={{ fontSize: '13px', color: '#666', marginTop: 0 }}>(or click to browse)</p>
          </>
        ) : (
          <div style={{ width: '100%' }}>
            {acceptedFiles.map((file, index) => (
              <div
                key={file.name}
                style={{
                  backgroundColor: index % 2 === 0 ? '#FFFFFF' : '#F0F0F0',
                  padding: '12px 0',
                  textAlign: 'center',
                  width: '100%',
                  boxSizing: 'border-box',
                }}
              >
                📄 {file.name}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const styles = {
  dropArea: {
    border: '2px dashed #aaa',
    borderRadius: '8px',
    padding: '16px',
    margin: '10px auto',
    backgroundColor: '#f7f7f7',
    color: '#333',
    width: '100%',
    maxWidth: '600px',
    minHeight: '200px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    height: '250px',
  },
  content: {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    transition: 'all 0.3s ease', // smooth transition when layout changes
  }
};

export default FileDrop;
