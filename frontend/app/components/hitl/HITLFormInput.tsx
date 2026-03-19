"use client";

import { useState } from "react";

interface FormField {
  name: string;
  label?: string;
  type?: "string" | "enum";
  options?: string[];
  default?: string;
}

interface HITLFormInputProps {
  message: string;
  fields: FormField[];
  onResolve: (value: Record<string, unknown>) => void;
}

export default function HITLFormInput({ message, fields, onResolve }: HITLFormInputProps) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const field of fields) {
      init[field.name] = field.default ?? (field.type === "enum" && field.options?.length ? field.options[0] : "");
    }
    return init;
  });
  const [resolved, setResolved] = useState(false);

  const handleChange = (name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = () => {
    setResolved(true);
    onResolve(values);
  };

  if (resolved) {
    return (
      <div style={{ padding: "0.75rem", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "0.5rem", fontSize: "0.875rem", color: "#166534" }}>
        Input submitted.
      </div>
    );
  }

  return (
    <div style={{ border: "1px solid #a78bfa", borderRadius: "0.5rem", overflow: "hidden", background: "#f5f3ff" }}>
      <div style={{ padding: "0.75rem", borderBottom: "1px solid #c4b5fd" }}>
        <div style={{ fontWeight: 600, fontSize: "0.875rem", color: "#5b21b6", marginBottom: "0.25rem" }}>
          Input Required
        </div>
        <div style={{ fontSize: "0.8125rem", color: "#6d28d9" }}>{message}</div>
      </div>

      <div style={{ padding: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {fields.map((field) => (
          <div key={field.name}>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 500, color: "#5b21b6", marginBottom: "0.125rem" }}>
              {field.label || field.name}
            </label>
            {field.type === "enum" && field.options ? (
              <select
                value={values[field.name]}
                onChange={(e) => handleChange(field.name, e.target.value)}
                style={{ width: "100%", padding: "0.375rem", fontSize: "0.8125rem", border: "1px solid #d1d5db", borderRadius: "0.375rem" }}
              >
                {field.options.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={values[field.name]}
                onChange={(e) => handleChange(field.name, e.target.value)}
                style={{ width: "100%", padding: "0.375rem", fontSize: "0.8125rem", border: "1px solid #d1d5db", borderRadius: "0.375rem", boxSizing: "border-box" }}
              />
            )}
          </div>
        ))}
      </div>

      <div style={{ padding: "0.75rem", borderTop: "1px solid #c4b5fd" }}>
        <button
          onClick={handleSubmit}
          style={{ padding: "0.375rem 0.75rem", fontSize: "0.8125rem", fontWeight: 500, color: "#fff", background: "#7c3aed", border: "none", borderRadius: "0.375rem", cursor: "pointer" }}
        >
          Submit
        </button>
      </div>
    </div>
  );
}
