import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const links = [
  ["Dashboard", "/dashboard"],
  ["Pantry", "/pantry"],
  ["Generate", "/generate-meal"],
  ["Meals", "/meals"],
  ["Profile", "/profile"],
];

export function Navigation() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  return (
    <nav className="navigation" aria-label="Main navigation">
      <NavLink className="brand" to="/dashboard" aria-label="PantryIQ dashboard">
        <span className="brand-mark">P</span>
        <span>PantryIQ</span>
      </NavLink>
      <div className="nav-links">
        {links.map(([label, path]) => (
          <NavLink key={path} to={path}>
            {label}
          </NavLink>
        ))}
      </div>
      <button
        className="button button-ghost"
        onClick={() => {
          logout();
          navigate("/login");
        }}
      >
        Log out
      </button>
    </nav>
  );
}
