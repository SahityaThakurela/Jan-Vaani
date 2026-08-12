import {
  ArrowRight,
  Mic,
  Search,
  ShieldCheck,
  Languages,
  Sparkles,
} from "lucide-react";

export default function Landing({ onGetStarted, onLogin }) {
  return (
    <div className="landing-page">

      {/* ================= NAVBAR ================= */}
      <nav className="landing-navbar">

        <div className="landing-brand">
          <div className="landing-logo">
            <Sparkles size={22} />
          </div>

          <div>
            <h2>Jan Vaani</h2>
            <span>जन की आवाज़</span>
          </div>
        </div>

        <div className="landing-nav-actions">
          <button
            className="landing-login"
            onClick={onLogin}
          >
            Login
          </button>

          <button
            className="landing-get-started"
            onClick={onGetStarted}
          >
            Get Started
            <ArrowRight size={17} />
          </button>
        </div>

      </nav>


      {/* ================= HERO ================= */}
      <main className="landing-hero">

        <div className="landing-hero-content">

          <div className="landing-badge">
            <span></span>
            AI-powered government assistance
          </div>

          <h1>
            Government Schemes,
            <br />
            <span>In Your Voice.</span>
          </h1>

          <p>
            Jan Vaani helps you discover government schemes,
            understand your eligibility, and get answers in
            your own language — simply by speaking.
          </p>


          {/* CTA BUTTONS */}
          <div className="landing-cta">

            <button
              className="landing-primary-btn"
              onClick={onGetStarted}
            >
              <Mic size={21} />
              Ask Jan Vaani
              <ArrowRight size={18} />
            </button>

            <button
              className="landing-secondary-btn"
              onClick={onLogin}
            >
              <Search size={18} />
              Explore Schemes
            </button>

          </div>


          {/* TRUST */}
          <div className="landing-trust">

            <div>
              <ShieldCheck size={17} />
              Secure & Private
            </div>

            <div>
              <Languages size={17} />
              Hindi & English
            </div>

          </div>

        </div>


        {/* ================= VOICE CARD ================= */}
        <div className="landing-visual">

          <div className="voice-preview-card">

            <div className="voice-preview-header">
              <span className="online-dot"></span>
              Jan Vaani Assistant
            </div>


            <div className="voice-mic-area">

              <div className="voice-ring ring-one"></div>
              <div className="voice-ring ring-two"></div>

              <div className="voice-mic">
                <Mic size={42} />
              </div>

            </div>


            <h3>बोलिए, हम सुन रहे हैं</h3>

            <p>
              "मुझे किसानों के लिए सरकारी योजना बताइए"
            </p>


            <div className="voice-wave">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>

          </div>

        </div>

      </main>


      {/* ================= FEATURES ================= */}
      <section className="landing-features">

        <div className="landing-feature">

          <div className="feature-icon">
            <Mic size={21} />
          </div>

          <div>
            <h3>Ask by Voice</h3>
            <p>
              Speak naturally instead of filling long forms.
            </p>
          </div>

        </div>


        <div className="landing-feature">

          <div className="feature-icon">
            <Search size={21} />
          </div>

          <div>
            <h3>Find Schemes</h3>
            <p>
              Discover government schemes based on your needs.
            </p>
          </div>

        </div>


        <div className="landing-feature">

          <div className="feature-icon">
            <ShieldCheck size={21} />
          </div>

          <div>
            <h3>Check Eligibility</h3>
            <p>
              Understand which schemes you may qualify for.
            </p>
          </div>

        </div>

      </section>

    </div>
  );
}