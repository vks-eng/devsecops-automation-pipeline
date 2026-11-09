-- =============================================================================
-- ShieldOps: DevSecOps Automation Platform - PostgreSQL schema (REFERENCE ONLY)
--
-- GENERATED FILE - do not edit by hand.
-- Produced by: `alembic upgrade head` (revision 0001) on an empty PostgreSQL 16
-- database, followed by `pg_dump --schema-only --no-owner --no-privileges`.
--
-- Alembic migrations in backend/alembic/versions/ are the source of truth.
-- Apply the schema with:  cd backend && alembic upgrade head
-- =============================================================================

--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    actor_id integer,
    actor_email character varying(320) NOT NULL,
    action character varying(100) NOT NULL,
    resource_type character varying(50) NOT NULL,
    resource_id character varying(64) NOT NULL,
    outcome character varying(20) NOT NULL,
    ip_address character varying(64) NOT NULL,
    details jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: dependency_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dependency_items (
    id integer NOT NULL,
    scan_id integer NOT NULL,
    project_id integer NOT NULL,
    name character varying(200) NOT NULL,
    version character varying(100) NOT NULL,
    ecosystem character varying(32) NOT NULL,
    vulnerable boolean NOT NULL,
    vulnerability_count integer NOT NULL
);


--
-- Name: dependency_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dependency_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dependency_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dependency_items_id_seq OWNED BY public.dependency_items.id;


--
-- Name: findings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.findings (
    id integer NOT NULL,
    scan_id integer NOT NULL,
    project_id integer NOT NULL,
    category character varying(32) NOT NULL,
    finding_type character varying(32) NOT NULL,
    severity character varying(16) NOT NULL,
    rule_id character varying(200) NOT NULL,
    title character varying(500) NOT NULL,
    description text NOT NULL,
    component character varying(500) NOT NULL,
    installed_version character varying(100),
    fixed_version character varying(200),
    file_path character varying(500),
    line integer,
    reference_url character varying(500),
    recommendation text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: findings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.findings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: findings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.findings_id_seq OWNED BY public.findings.id;


--
-- Name: integration_credentials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.integration_credentials (
    id integer NOT NULL,
    project_id integer NOT NULL,
    provider character varying(32) NOT NULL,
    encrypted_token text NOT NULL,
    token_hint character varying(16) NOT NULL,
    created_by_id integer,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: integration_credentials_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.integration_credentials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: integration_credentials_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.integration_credentials_id_seq OWNED BY public.integration_credentials.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    project_id integer,
    type character varying(40) NOT NULL,
    severity character varying(16) NOT NULL,
    title character varying(300) NOT NULL,
    message text NOT NULL,
    link character varying(300) NOT NULL,
    read_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: pipeline_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_runs (
    id integer NOT NULL,
    project_id integer NOT NULL,
    external_id character varying(64) NOT NULL,
    workflow_name character varying(200) NOT NULL,
    branch character varying(200) NOT NULL,
    commit_sha character varying(64) NOT NULL,
    event character varying(50) NOT NULL,
    status character varying(32) NOT NULL,
    conclusion character varying(32),
    actor character varying(100) NOT NULL,
    html_url character varying(500) NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    duration_seconds integer,
    source character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: pipeline_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pipeline_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pipeline_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pipeline_runs_id_seq OWNED BY public.pipeline_runs.id;


--
-- Name: project_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_members (
    id integer NOT NULL,
    project_id integer NOT NULL,
    user_id integer NOT NULL,
    role character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: project_members_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_members_id_seq OWNED BY public.project_members.id;


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    slug character varying(64) NOT NULL,
    description text NOT NULL,
    team character varying(120) NOT NULL,
    repo_url character varying(300) NOT NULL,
    repo_owner character varying(100) NOT NULL,
    repo_name character varying(100) NOT NULL,
    default_branch character varying(200) NOT NULL,
    branches jsonb NOT NULL,
    sonar_project_key character varying(400),
    container_images jsonb NOT NULL,
    scan_config jsonb NOT NULL,
    owner_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: scans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scans (
    id integer NOT NULL,
    project_id integer NOT NULL,
    scan_type character varying(32) NOT NULL,
    target character varying(300) NOT NULL,
    status character varying(20) NOT NULL,
    adapter_mode character varying(20) NOT NULL,
    triggered_by_id integer,
    trigger character varying(20) NOT NULL,
    summary jsonb NOT NULL,
    quality_gate_status character varying(20),
    metadata jsonb NOT NULL,
    error text,
    created_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone
);


--
-- Name: scans_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scans_id_seq OWNED BY public.scans.id;


--
-- Name: score_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.score_snapshots (
    id integer NOT NULL,
    project_id integer NOT NULL,
    score double precision NOT NULL,
    grade character varying(2) NOT NULL,
    counts jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: score_snapshots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.score_snapshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: score_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.score_snapshots_id_seq OWNED BY public.score_snapshots.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(320) NOT NULL,
    full_name character varying(200) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: dependency_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dependency_items ALTER COLUMN id SET DEFAULT nextval('public.dependency_items_id_seq'::regclass);


--
-- Name: findings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.findings ALTER COLUMN id SET DEFAULT nextval('public.findings_id_seq'::regclass);


--
-- Name: integration_credentials id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credentials ALTER COLUMN id SET DEFAULT nextval('public.integration_credentials_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: pipeline_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_runs ALTER COLUMN id SET DEFAULT nextval('public.pipeline_runs_id_seq'::regclass);


--
-- Name: project_members id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_members ALTER COLUMN id SET DEFAULT nextval('public.project_members_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: scans id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scans ALTER COLUMN id SET DEFAULT nextval('public.scans_id_seq'::regclass);


--
-- Name: score_snapshots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_snapshots ALTER COLUMN id SET DEFAULT nextval('public.score_snapshots_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_logs pk_audit_logs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT pk_audit_logs PRIMARY KEY (id);


--
-- Name: dependency_items pk_dependency_items; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dependency_items
    ADD CONSTRAINT pk_dependency_items PRIMARY KEY (id);


--
-- Name: findings pk_findings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.findings
    ADD CONSTRAINT pk_findings PRIMARY KEY (id);


--
-- Name: integration_credentials pk_integration_credentials; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credentials
    ADD CONSTRAINT pk_integration_credentials PRIMARY KEY (id);


--
-- Name: notifications pk_notifications; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT pk_notifications PRIMARY KEY (id);


--
-- Name: pipeline_runs pk_pipeline_runs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_runs
    ADD CONSTRAINT pk_pipeline_runs PRIMARY KEY (id);


--
-- Name: project_members pk_project_members; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT pk_project_members PRIMARY KEY (id);


--
-- Name: projects pk_projects; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT pk_projects PRIMARY KEY (id);


--
-- Name: scans pk_scans; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scans
    ADD CONSTRAINT pk_scans PRIMARY KEY (id);


--
-- Name: score_snapshots pk_score_snapshots; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_snapshots
    ADD CONSTRAINT pk_score_snapshots PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: integration_credentials uq_integration_credentials_pair; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credentials
    ADD CONSTRAINT uq_integration_credentials_pair UNIQUE (project_id, provider);


--
-- Name: pipeline_runs uq_pipeline_runs_external; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_runs
    ADD CONSTRAINT uq_pipeline_runs_external UNIQUE (project_id, external_id);


--
-- Name: project_members uq_project_members_pair; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT uq_project_members_pair UNIQUE (project_id, user_id);


--
-- Name: projects uq_projects_repo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT uq_projects_repo UNIQUE (repo_owner, repo_name);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: ix_dependency_items_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dependency_items_project_id ON public.dependency_items USING btree (project_id);


--
-- Name: ix_dependency_items_scan_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dependency_items_scan_id ON public.dependency_items USING btree (scan_id);


--
-- Name: ix_findings_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_findings_project_id ON public.findings USING btree (project_id);


--
-- Name: ix_findings_scan_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_findings_scan_id ON public.findings USING btree (scan_id);


--
-- Name: ix_findings_severity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_findings_severity ON public.findings USING btree (severity);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_notifications_user_unread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_user_unread ON public.notifications USING btree (user_id, read_at);


--
-- Name: ix_pipeline_runs_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pipeline_runs_project_id ON public.pipeline_runs USING btree (project_id);


--
-- Name: ix_projects_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_projects_slug ON public.projects USING btree (slug);


--
-- Name: ix_scans_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scans_project_id ON public.scans USING btree (project_id);


--
-- Name: ix_scans_scan_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scans_scan_type ON public.scans USING btree (scan_type);


--
-- Name: ix_score_snapshots_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_score_snapshots_project_id ON public.score_snapshots USING btree (project_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: audit_logs fk_audit_logs_actor_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT fk_audit_logs_actor_id_users FOREIGN KEY (actor_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: dependency_items fk_dependency_items_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dependency_items
    ADD CONSTRAINT fk_dependency_items_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: dependency_items fk_dependency_items_scan_id_scans; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dependency_items
    ADD CONSTRAINT fk_dependency_items_scan_id_scans FOREIGN KEY (scan_id) REFERENCES public.scans(id) ON DELETE CASCADE;


--
-- Name: findings fk_findings_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.findings
    ADD CONSTRAINT fk_findings_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: findings fk_findings_scan_id_scans; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.findings
    ADD CONSTRAINT fk_findings_scan_id_scans FOREIGN KEY (scan_id) REFERENCES public.scans(id) ON DELETE CASCADE;


--
-- Name: integration_credentials fk_integration_credentials_created_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credentials
    ADD CONSTRAINT fk_integration_credentials_created_by_id_users FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: integration_credentials fk_integration_credentials_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.integration_credentials
    ADD CONSTRAINT fk_integration_credentials_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: notifications fk_notifications_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT fk_notifications_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: notifications fk_notifications_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT fk_notifications_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: pipeline_runs fk_pipeline_runs_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_runs
    ADD CONSTRAINT fk_pipeline_runs_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_members fk_project_members_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT fk_project_members_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: project_members fk_project_members_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT fk_project_members_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: projects fk_projects_owner_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT fk_projects_owner_id_users FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: scans fk_scans_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scans
    ADD CONSTRAINT fk_scans_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: scans fk_scans_triggered_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scans
    ADD CONSTRAINT fk_scans_triggered_by_id_users FOREIGN KEY (triggered_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: score_snapshots fk_score_snapshots_project_id_projects; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_snapshots
    ADD CONSTRAINT fk_score_snapshots_project_id_projects FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

