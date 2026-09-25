import {
  CfnParameter,
  RemovalPolicy,
  Stack,
  StackProps,
  aws_ecr as ecr,
  aws_ecs as ecs,
  aws_logs as logs,
  aws_secretsmanager as secretsmanager,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface DatabaseOperationsStackProps extends StackProps {
  applicationName: string;
  applicationUserSecret: secretsmanager.ISecret;
  databaseBootstrapTaskCpu: number;
  databaseBootstrapTaskMemoryMiB: number;
  databaseHost: string;
  databaseName: string;
  environmentName: string;
  masterUserSecretArn: string;
  migrationUserSecret: secretsmanager.ISecret;
  repository: ecr.IRepository;
}

export class DatabaseOperationsStack extends Stack {
  constructor(scope: Construct, id: string, props: DatabaseOperationsStackProps) {
    super(scope, id, props);

    const databaseBootstrapLogGroup = new logs.LogGroup(this, "DatabaseBootstrapLogGroup", {
      logGroupName: `/ecs/${props.applicationName}-${props.environmentName}-db-bootstrap`,
      removalPolicy: RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.TWO_MONTHS,
    });

    const databaseBootstrapImageTag = new CfnParameter(this, "DatabaseBootstrapImageTag", {
      description: "Git commit SHA used as the DB bootstrap ECR image tag",
      type: "String",
    });

    const masterUserSecret = secretsmanager.Secret.fromSecretCompleteArn(
      this,
      "MasterUserSecret",
      props.masterUserSecretArn,
    );

    const taskDefinition = new ecs.FargateTaskDefinition(this, "DatabaseBootstrapTaskDefinition", {
      cpu: props.databaseBootstrapTaskCpu,
      memoryLimitMiB: props.databaseBootstrapTaskMemoryMiB,
    });

    taskDefinition.addContainer("DatabaseBootstrapContainer", {
      command: ["/app/.venv/bin/python", "-m", "app.bootstrap_db"],
      environment: {
        DB_HOST: props.databaseHost,
        DB_NAME: props.databaseName,
        DB_SSL_ROOT_CERT: "/app/certs/rds-ca-bundle.pem",
      },
      image: ecs.ContainerImage.fromEcrRepository(
        props.repository,
        databaseBootstrapImageTag.valueAsString,
      ),
      logging: ecs.LogDrivers.awsLogs({
        logGroup: databaseBootstrapLogGroup,
        streamPrefix: "db-bootstrap",
      }),
      secrets: {
        DB_ADMIN_USERNAME: ecs.Secret.fromSecretsManager(masterUserSecret, "username"),
        DB_ADMIN_PASSWORD: ecs.Secret.fromSecretsManager(masterUserSecret, "password"),
        DB_MIGRATION_USERNAME: ecs.Secret.fromSecretsManager(props.migrationUserSecret, "username"),
        DB_MIGRATION_PASSWORD: ecs.Secret.fromSecretsManager(props.migrationUserSecret, "password"),
        DB_APP_USERNAME: ecs.Secret.fromSecretsManager(props.applicationUserSecret, "username"),
        DB_APP_PASSWORD: ecs.Secret.fromSecretsManager(props.applicationUserSecret, "password"),
      },
    });
  }
}
