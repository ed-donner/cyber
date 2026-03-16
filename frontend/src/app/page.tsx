'use client'

import { useState } from 'react';
import { AnalysisResponse } from '@/types/security';
import CodeInput from '@/components/CodeInput';
import AnalysisResults from '@/components/AnalysisResults';

// Force relative URLs in production builds
// Only use localhost when explicitly running in development mode
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 
  (process.env.NODE_ENV === 'development' && typeof window !== 'undefined' && window.location?.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : '');


/**
 * Main application page for cybersecurity code analysis
 */
export default function Home() {
  const [codeContent, setCodeContent] = useState('');
  const [fileName, setFileName] = useState('');
  const [analysisResults, setAnalysisResults] = useState<AnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.name.endsWith('.py')) {
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        setCodeContent(content);
        setAnalysisResults(null);
        setError(null);
      };
      reader.readAsText(file);
    } else {
      alert('Please select a Python (.py) file');
    }
  };

  const handleAnalyzeCode = async () => {
    if (!codeContent) {
      alert('Please upload a Python file first');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: codeContent, file_name: fileName }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const results: AnalysisResponse = await response.json();
      setAnalysisResults(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during analysis');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Cybersecurity Analyst</h1>
          <p className="text-accent mt-2">Python code analysis tool for security assessment</p>
        </header>

        <div className="grid grid-rows-2 gap-6 h-[calc(100vh-200px)]">
          <CodeInput
            codeContent={codeContent}
            fileName={fileName}
            onFileUpload={handleFileUpload}
            onAnalyzeCode={handleAnalyzeCode}
            isAnalyzing={isAnalyzing}
          />
          
          <AnalysisResults
            analysisResults={analysisResults}
            isAnalyzing={isAnalyzing}
            error={error}
          />
        </div>
      </div>
    </div>
  );
}