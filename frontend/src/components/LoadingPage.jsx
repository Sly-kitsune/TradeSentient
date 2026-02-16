import React from 'react';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';

export function LoadingPage() {
    return (
        <div className="loading-container">
            <div className="lottie-wrapper">
                <video
                    src="/animations/loading.webm"
                    autoPlay
                    loop
                    muted
                    playsInline
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
            </div>
            <h2>Fetching Market Data...</h2>
        </div>
    );
}
