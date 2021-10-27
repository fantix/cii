CREATE MIGRATION m1oklz7yk7ahcpsk2cblhesax676saaso6pvd6om4vuk6himvbqsoq
    ONTO initial
{
  CREATE TYPE default::Workflow {
      CREATE REQUIRED PROPERTY name -> std::str;
  };
};
