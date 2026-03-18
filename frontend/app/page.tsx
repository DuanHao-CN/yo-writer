import Link from "next/link";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <h1>YoAgent</h1>
        <p>Agent-as-a-Service Platform</p>
        <Link
          href="/agents"
          style={{
            marginTop: "1.5rem",
            padding: "0.625rem 1.5rem",
            background: "#3b82f6",
            color: "white",
            borderRadius: "0.375rem",
            textDecoration: "none",
            fontSize: "0.875rem",
            fontWeight: 500,
          }}
        >
          View Agents
        </Link>
      </main>
    </div>
  );
}
