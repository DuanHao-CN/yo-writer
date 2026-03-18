import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <h1>YoAgent</h1>
        <p>Agent-as-a-Service Platform</p>
      </main>
    </div>
  );
}
